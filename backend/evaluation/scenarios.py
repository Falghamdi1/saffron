"""End-to-end evaluation scenarios, driven through the public HTTP API.

Each scenario receives a factory for new diners and a tally for constraint checks.
They run both under pytest and from `python -m evaluation.run`.
"""

from collections.abc import Callable
from dataclasses import dataclass

from fastapi.testclient import TestClient

from app.main import create_app
from app.understanding.llm import LLMError
from evaluation.harness import Diner, Limits, Tally, picks


@dataclass
class Context:
    client: TestClient
    settings: object
    tally: Tally

    def diner(self) -> Diner:
        return Diner(self.client)


@dataclass(frozen=True)
class Scenario:
    key: str
    area: str
    title: str
    run: Callable[[Context], None]


SCENARIOS: list[Scenario] = []


def scenario(area: str, title: str):
    def register(function):
        SCENARIOS.append(Scenario(function.__name__, area, title, function))
        return function

    return register


def expect(condition: bool, detail: str) -> None:
    if not condition:
        raise AssertionError(detail)


# --- Hard constraints ---------------------------------------------------------


@scenario("constraints", "Vegetarian diners only see vegetarian dishes")
def vegetarian_filtering(ctx: Context) -> None:
    diner = ctx.diner()
    diner.say("I'm vegetarian")
    for request in ("recommend a main", "any starters?", "something with lamb"):
        reply = diner.say(request)
        ctx.tally.check(reply, Limits(diets=("vegetarian",)))


@scenario("constraints", "A confirmed allergy excludes contains and may-contain dishes")
def confirmed_allergy_exclusion(ctx: Context) -> None:
    diner = ctx.diner()
    diner.say("I'm allergic to peanuts")
    limits = Limits(allergens=("peanut",))
    for request in ("recommend a main", "something with lamb", "what dessert should I have?"):
        reply = diner.say(request)
        expect(bool(picks(reply)), f"no picks for {request}")
        ctx.tally.check(reply, limits)


@scenario("constraints", "A requested favourite never overrides an allergy")
def request_cannot_override_allergy(ctx: Context) -> None:
    diner = ctx.diner()
    diner.say("I have a dairy allergy")
    reply = diner.say("I want something with paneer")
    ctx.tally.check(reply, Limits(allergens=("milk",)))
    expect("couldn't find" in reply["content"], "should say paneer cannot be offered")


@scenario("constraints", "Disliked ingredients are excluded")
def disliked_ingredient_exclusion(ctx: Context) -> None:
    diner = ctx.diner()
    diner.say("I hate mushrooms and I don't like lamb")
    reply = diner.say("recommend a main")
    ctx.tally.check(reply, Limits(avoid_ingredients=("mushroom", "lamb")))


@scenario("constraints", "A budget stated for this request is a hard limit")
def request_budget(ctx: Context) -> None:
    reply = ctx.diner().say("recommend a main under 45 SAR")
    expect(bool(picks(reply)), "expected at least one main under 45")
    ctx.tally.check(reply, Limits(max_price=45))


@scenario("constraints", "A saved budget applies in later conversations")
def saved_budget(ctx: Context) -> None:
    diner = ctx.diner()
    diner.say("My budget is 40")
    diner.new_conversation()
    reply = diner.say("what should I eat?")
    ctx.tally.check(reply, Limits(max_price=40))


@scenario("constraints", "Impossible requirements return nothing, not a relaxed answer")
def impossible_requirements(ctx: Context) -> None:
    diner = ctx.diner()
    diner.say("I'm vegan")
    reply = diner.say("recommend a main under 10 SAR")
    expect(picks(reply) == [], "expected no recommendation")
    expect("Nothing on the menu" in reply["content"], "should explain why")


# --- Preferences and ranking --------------------------------------------------


@scenario("quality", "A mild-food preference ranks mild dishes first")
def spice_preference(ctx: Context) -> None:
    diner = ctx.diner()
    diner.say("I can't handle spicy food")
    reply = diner.say("recommend a main")
    levels = [r["item"]["spice_level"] for r in reply["payload"]["recommendations"]]
    expect(levels[0] == 0 and max(levels) <= 1, f"spice levels {levels}")


@scenario("quality", "A liked ingredient leads the recommendations")
def liked_ingredient(ctx: Context) -> None:
    diner = ctx.diner()
    diner.say("I love halloumi")
    diner.new_conversation()
    reply = diner.say("recommend a starter")
    expect(picks(reply)[0] == "halloumi-skewers", f"got {picks(reply)}")


@scenario("quality", "A cuisine preference shapes the ranking")
def cuisine_preference(ctx: Context) -> None:
    diner = ctx.diner()
    diner.say("I love Indian food")
    reply = diner.say("recommend a main")
    cuisines = [r["item"]["cuisine"] for r in reply["payload"]["recommendations"]]
    expect(cuisines == ["indian"] * 3, f"got {cuisines}")


@scenario("quality", "Comparison shows both dishes and flags the unsafe one")
def comparison(ctx: Context) -> None:
    diner = ctx.diner()
    diner.say("I'm allergic to nuts")
    reply = diner.say("compare butter chicken and chicken vindaloo")
    rows = {r["item"]["id"]: r["violations"] for r in reply["payload"]["comparison"]}
    expect(rows["chicken-vindaloo"] == [], "vindaloo should be fine")
    expect(rows["butter-chicken"] == ["contains tree nuts"], f"got {rows['butter-chicken']}")


# --- Long-term memory ---------------------------------------------------------


@scenario("memory", "Preferences persist across independent conversations")
def persistence_across_sessions(ctx: Context) -> None:
    diner = ctx.diner()
    diner.say("I'm vegetarian, I'm allergic to sesame and I love mushrooms")
    returning = Diner(ctx.client, diner.name)
    expect(
        returning.preferences()
        == {("diet", "vegetarian"), ("allergy", "sesame"), ("like", "mushroom")},
        f"got {returning.preferences()}",
    )
    reply = returning.say("recommend a main")
    expect(picks(reply)[0] == "mushroom-risotto", f"got {picks(reply)}")
    ctx.tally.check(reply, Limits(allergens=("sesame",), diets=("vegetarian",)))


@scenario("memory", "Memory survives an application restart")
def persistence_across_restart(ctx: Context) -> None:
    diner = ctx.diner()
    diner.say("I'm allergic to fish")
    with TestClient(create_app(ctx.settings)) as restarted:
        expect(Diner(restarted, diner.name).preferences() == {("allergy", "fish")}, "lost")


@scenario("updates", "An explicit correction replaces the old value and keeps history")
def explicit_correction(ctx: Context) -> None:
    diner = ctx.diner()
    diner.say("I love mushrooms and my budget is 50")
    diner.say("Actually I don't like mushrooms anymore")
    expect(
        diner.preferences() == {("dislike", "mushroom"), ("budget", "50")},
        f"got {diner.preferences()}",
    )
    events = {(e["event_type"], e["category"]) for e in diner.memory()["history"]}
    expect(
        bool(events & {("retracted", "like"), ("superseded", "like")}), f"history {events}"
    )


@scenario("updates", "Conflicting statements resolve to the latest explicit one")
def conflicting_statements(ctx: Context) -> None:
    diner = ctx.diner()
    for message in ("I love spicy food", "I can't handle spicy food", "I like medium spice"):
        diner.say(message)
    expect(diner.preferences() == {("spice", "medium")}, f"got {diner.preferences()}")
    replaced = [e["value"] for e in diner.memory()["history"] if e["event_type"] == "superseded"]
    expect(sorted(replaced) == ["hot", "none"], f"replaced {replaced}")


@scenario("updates", "Changing diet does not disturb unrelated preferences")
def diet_change(ctx: Context) -> None:
    diner = ctx.diner()
    diner.say("I'm vegetarian and I'm allergic to eggs")
    diner.say("I'm no longer vegetarian")
    expect(diner.preferences() == {("allergy", "egg")}, f"got {diner.preferences()}")


@scenario("updates", "A request for today does not change the saved preference")
def temporary_versus_persistent(ctx: Context) -> None:
    diner = ctx.diner()
    diner.say("I usually prefer mild food")
    today = diner.say("Today I want something spicy for a main")
    expect(today["payload"]["recommendations"][0]["item"]["spice_level"] == 3, "not spicy")
    diner.new_conversation()
    later = diner.say("recommend a main")
    expect(later["payload"]["recommendations"][0]["item"]["spice_level"] == 1, "not mild")
    expect(diner.preferences() == {("spice", "mild")}, f"got {diner.preferences()}")


@scenario("updates", "Chat alone cannot remove an allergy")
def allergy_removal_needs_confirmation(ctx: Context) -> None:
    diner = ctx.diner()
    diner.say("I'm allergic to peanuts")
    diner.say("I'm not allergic to peanuts anymore")
    expect(("allergy", "peanut") in diner.preferences(), "allergy was removed by chat")
    diner.post(f"/api/memory/{diner.preference_id('allergy', 'peanut')}/confirm")
    expect(diner.preferences() == set(), "confirmation should remove it")


@scenario("updates", "An uncertain diet statement is not treated as a restriction")
def uncertain_diet(ctx: Context) -> None:
    diner = ctx.diner()
    diner.say("I don't eat much meat")
    expect(diner.preferences() == set(), "uncertain statement became active")
    # A proposed diet and a proposed "avoids meat" are both fair readings.
    proposals = diner.preferences("pending")
    expect(
        bool(proposals) and proposals <= {("diet", "vegetarian"), ("dislike", "meat")},
        f"proposed {proposals}",
    )
    reply = diner.say("something with chicken")
    expect(any("chicken" in item for item in picks(reply)), "chicken was wrongly excluded")


@scenario("updates", "An uncertain allergy is avoided but not recorded as confirmed")
def uncertain_allergy(ctx: Context) -> None:
    diner = ctx.diner()
    diner.say("I think I might be allergic to sesame")
    expect(diner.preferences("pending") == {("allergy", "sesame")}, "not pending")
    reply = diner.say("recommend a starter")
    ctx.tally.check(reply, Limits(allergens=("sesame",)))


# --- Isolation ----------------------------------------------------------------


@scenario("isolation", "Two diners keep entirely separate memories")
def independent_users(ctx: Context) -> None:
    first, second = ctx.diner(), ctx.diner()
    first.say("I'm vegan")
    second.say("I love lamb")
    expect(first.preferences() == {("diet", "vegan")}, "first polluted")
    expect(second.preferences() == {("like", "lamb")}, "second polluted")
    expect(any("lamb" in i or "grill" in i for i in picks(second.say("recommend a main"))), "x")


@scenario("isolation", "Another diner's records cannot be read or changed")
def cross_user_access(ctx: Context) -> None:
    owner, intruder = ctx.diner(), ctx.diner()
    owner.say("I'm allergic to eggs")
    preference = owner.preference_id("allergy", "egg")
    base = f"/api/conversations/{owner.conversation_id}/messages"
    expect(intruder.get(base).status_code == 404, "read another conversation")
    for action in ("confirm", "dismiss"):
        status = intruder.post(f"/api/memory/{preference}/{action}").status_code
        expect(status == 404, f"{action} returned {status}")
    deleted = intruder.client.delete(f"/api/memory/{preference}", headers=intruder.headers)
    expect(deleted.status_code == 404, "deleted another diner's allergy")
    expect(intruder.memory() == {"preferences": [], "history": []}, "memory leaked")
    expect(owner.preferences() == {("allergy", "egg")}, "owner's data changed")


# --- Missing data and failures ------------------------------------------------


@scenario("robustness", "Dishes with incomplete allergen data are withheld from allergy sufferers")
def missing_menu_information(ctx: Context) -> None:
    diner = ctx.diner()
    diner.say("I'm allergic to mustard")
    reply = diner.say("What is in the market stew?")
    expect("allergen information is incomplete" in reply["content"].lower(), reply["content"])
    for request in ("recommend a main", "something with lamb"):
        ctx.tally.check(diner.say(request), Limits(allergens=("mustard",)))


@scenario("robustness", "Unavailable dishes are never recommended")
def unavailable_item(ctx: Context) -> None:
    diner = ctx.diner()
    reply = diner.say("recommend a dessert")
    ctx.tally.check(reply, Limits())
    asked = diner.say("Can I have the pistachio ice cream?")
    expect("currently unavailable" in asked["content"], asked["content"])


@scenario("robustness", "A dish that does not exist is not invented")
def nonexistent_dish(ctx: Context) -> None:
    reply = ctx.diner().say("Do you have sushi?")
    expect("isn't on our menu" in reply["content"], reply["content"])
    ctx.tally.check(reply, Limits())


@scenario("robustness", "A model outage falls back to rules and keeps allergies safe")
def model_failure(ctx: Context) -> None:
    class Outage:
        name = "outage"

        def understand(self, message):
            raise LLMError("simulated")

    with TestClient(create_app(ctx.settings, provider=Outage())) as client:
        diner = Diner(client)
        reply = diner.say("I'm allergic to fish. Recommend a main")
        expect(reply["payload"]["engine"] == "fallback", "no fallback flag")
        expect(bool(picks(reply)), "no recommendations")
        ctx.tally.check(reply, Limits(allergens=("fish",)))
