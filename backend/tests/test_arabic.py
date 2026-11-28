"""Arabic input must reach the same structured memory and safety rules as English."""

import re

import pytest
from fastapi.testclient import TestClient

from app import language
from app.chat import context
from app.config import ROOT_DIR
from app.i18n import ARABIC_VALUES, STRINGS
from app.main import create_app
from app.memory.policy import normalize
from app.schemas import Candidate, Understanding
from app.setup_db import load_menu_file
from app.understanding.rules import understand as rules
from app.understanding.service import understand
from evaluation.harness import Diner, Limits, picks, violations_by_oracle

MENU = {item.id: item for item in load_menu_file()}


class Model:
    name = "scripted"

    def __init__(self, result: Understanding) -> None:
        self.result = result

    def understand(self, message):
        return self.result.model_copy(deep=True)


def saved(result: Understanding) -> set[tuple[str, str, str]]:
    return {
        (c.category, c.value, c.operation)
        for candidate in result.preferences if candidate.scope == "persistent"
        for c in normalize(candidate)
    }


def table(result: Understanding) -> list[str]:
    return context.clean(result.request).allergies


@pytest.mark.parametrize(("word", "expected"), [
    ("السمسم", {"sesame"}), ("سمسم", {"sesame"}), ("الطحينة", {"sesame"}),
    ("المكسرات", {"peanut", "tree_nut"}), ("للمكسرات", {"peanut", "tree_nut"}),
    ("الفول السوداني", {"peanut"}), ("اللوز", {"tree_nut"}), ("الحليب", {"milk"}),
    ("منتجات الألبان", {"milk"}), ("البيض", {"egg"}), ("السمك", {"fish"}),
    ("الروبيان", {"crustacean"}), ("الجمبري", {"crustacean"}), ("القمح", {"gluten"}),
    ("الخردل", {"mustard"}),
])
def test_arabic_allergen_words_reach_the_same_canonical_values(word, expected):
    got = {c.value for c in normalize(Candidate(category="allergy", value=word))}
    assert got == expected


@pytest.mark.parametrize(("message", "expected"), [
    ("عندي حساسية من السمسم", {("allergy", "sesame", "assert")}),
    ("أنا أتحسس من البيض والسمك", {("allergy", "egg", "assert"), ("allergy", "fish", "assert")}),
    ("عندي حساسية من السمسم، وش تنصحني للعشا؟", {("allergy", "sesame", "assert")}),
    ("ما عندي حساسية من السمسم", {("allergy", "sesame", "retract")}),
    ("أنا نباتي", {("diet", "vegetarian", "assert")}),
    ("ما عدت نباتي", {("diet", "vegetarian", "retract")}),
    ("أحب الأكل الحار", {("spice", "hot", "assert")}),
    ("ما أحب الأكل الحار", {("spice", "none", "assert")}),
    ("أحب الدجاج", {("like", "chicken", "assert")}),
    ("ما أحب الفطر", {("dislike", "mushroom", "assert")}),
    ("ميزانيتي ٦٠ ريال", {("budget", "60", "assert")}),
])
def test_rules_read_clear_arabic_statements(message, expected):
    assert saved(rules(message)) == expected


def test_a_price_limit_with_arabic_digits():
    assert rules("أبي شي أقل من ٤٥ ريال").request.max_price == 45


def test_wanting_something_is_not_a_statement_about_my_father():
    result = rules("أبي شي حار")
    assert result.request.spice == 3
    assert saved(result) == set()
    assert table(result) == []
    assert saved(rules("أبي أقول إن عندي حساسية من السمسم")) == {("allergy", "sesame", "assert")}


@pytest.mark.parametrize("message", [
    "زوجتي عندها حساسية من السمسم، وش تنصحني لها؟",
    "ولدي عنده حساسية من السمسم",
    "هل الحمص مناسب لشخص عنده حساسية من السمسم؟",
])
def test_another_diners_allergy_in_arabic_is_for_the_chat_only(message):
    result = rules(message)
    assert saved(result) == set()
    assert table(result) == ["sesame"]


def test_an_allergy_shared_in_arabic_is_remembered():
    result = rules("أنا وزوجتي عندنا حساسية من السمسم")
    assert ("allergy", "sesame", "assert") in saved(result)


def test_a_hedged_arabic_allergy_stays_uncertain():
    candidate = rules("أظن عندي حساسية من السمسم").preferences[0]
    assert candidate.certainty == "uncertain"


def test_a_model_cannot_save_another_persons_allergy_from_arabic():
    message = "ولدي عنده حساسية من الفول السوداني"
    wrong = Understanding(preferences=[
        Candidate(category="allergy", value="peanut", evidence="حساسية من الفول السوداني")
    ])
    result, _ = understand(message, Model(wrong))
    assert result.preferences == []
    assert table(result) == ["peanut"]


def test_a_quote_that_differs_only_in_spelling_marks_is_still_evidence():
    message = "أنا أحبّ الدجاجَ"
    model = Understanding(preferences=[
        Candidate(category="like", value="chicken", evidence="انا احب الدجاج")
    ])
    result, _ = understand(message, Model(model))
    assert saved(result) == {("like", "chicken", "assert")}


def test_an_arabic_value_from_the_model_filters_the_menu(settings):
    model = Understanding(intent="recommend", preferences=[
        Candidate(category="allergy", value="السمسم", evidence="حساسية من السمسم")
    ])
    with TestClient(create_app(settings, provider=Model(model))) as client:
        diner = Diner(client)
        reply = diner.say("عندي حساسية من السمسم")
        assert diner.preferences() == {("allergy", "sesame")}
        assert picks(reply)
        for item in picks(reply):
            assert violations_by_oracle(item, Limits(allergens=("sesame",))) == []


def test_an_allergy_that_cannot_be_identified_withholds_suggestions(diner):
    reply = diner.say("عندي حساسية من الترمس. وش تنصحني؟")
    assert picks(reply) == []
    assert diner.preferences() == set()
    assert diner.preferences("pending") == {("allergy", "الترمس")}
    assert picks(diner.say("recommend a main")) == []


def test_memory_is_shared_between_arabic_and_english(diner):
    diner.say("عندي حساسية من السمسم وأحب الأكل الحار")
    diner.new_conversation()
    reply = diner.say("recommend a main")
    assert diner.preferences() == {("allergy", "sesame"), ("spice", "hot")}
    assert MENU[picks(reply)[0]].spice_level == 3
    for item in picks(reply):
        assert violations_by_oracle(item, Limits(allergens=("sesame",))) == []


def test_memory_stated_in_english_applies_to_an_arabic_conversation(diner):
    diner.say("I'm allergic to sesame")
    diner.new_conversation()
    reply = diner.say("وش تنصحني للعشا؟")
    assert picks(reply)
    for item in picks(reply):
        assert violations_by_oracle(item, Limits(allergens=("sesame",))) == []
    assert diner.preferences() == {("allergy", "sesame")}


def test_saying_the_same_thing_in_both_languages_keeps_one_record(diner):
    diner.say("I love chicken")
    diner.say("أحب الدجاج")
    assert [p["value"] for p in diner.memory()["preferences"]] == ["chicken"]


@pytest.mark.parametrize("message", [
    "ابي حلى بدون مكسرات", "عطني حلى ما فيه مكسرات", "ابي حلى من غير مكسرات",
])
def test_asking_for_something_without_a_food_never_asks_for_it(message):
    request = rules(message).request
    assert request.wants == []
    assert request.avoid == ["nut"]
    assert request.category == "dessert"


def test_every_dish_has_arabic_text_matching_its_english_facts():
    for item in MENU.values():
        assert language.is_arabic(item.name_ar) and language.is_arabic(item.description_ar)
        assert len(item.ingredients_ar) == len(item.ingredients), item.id
        assert all(language.is_arabic(i) for i in item.ingredients_ar), item.id


def test_both_languages_have_the_same_sentences_and_placeholders():
    english, arabic_text = STRINGS["en"], STRINGS["ar"]
    assert set(english) == set(arabic_text)
    for key, text in english.items():
        wanted = set(re.findall(r"{(\w+)}", text))
        # Arabic may drop a count, but must never need a value English does not supply.
        assert set(re.findall(r"{(\w+)}", arabic_text[key])) <= wanted, key


def test_an_arabic_message_gets_an_arabic_answer_with_the_same_prices(diner):
    reply = diner.say("عندي حساسية من السمسم، وش تنصحني للعشا؟")
    payload = reply["payload"]
    assert payload["lang"] == "ar"
    assert "حفظت" in reply["content"] and "السمسم" in payload["notice"]
    for entry in payload["recommendations"]:
        item = MENU[entry["item"]["id"]]
        assert entry["item"] == item.model_dump()
        assert item.name_ar in reply["content"]
        assert all(language.is_arabic(reason) for reason in entry["reasons"])


def test_a_dish_asked_about_by_its_arabic_name_is_checked(diner):
    diner.say("عندي حساسية من السمسم")
    reply = diner.say("هل عندكم حمص كلاسيكي؟")
    assert [c["item"]["id"] for c in reply["payload"]["comparison"]] == ["hummus"]
    assert "لا أنصحك به" in reply["content"]
    assert "22 ر.س" in reply["content"]


def test_menu_explanations_follow_the_requested_language(diner):
    diner.say("I'm allergic to sesame")
    arabic_menu = {i["id"]: i for i in diner.get("/api/menu?lang=ar").json()}
    english_menu = {i["id"]: i for i in diner.get("/api/menu").json()}
    assert english_menu["hummus"]["violations"] == ["contains sesame"]
    assert arabic_menu["hummus"]["violations"] == ["يحتوي على السمسم"]
    assert [bool(i["violations"]) for i in arabic_menu.values()] == [
        bool(i["violations"]) for i in english_menu.values()
    ]


# The sample prompts offered by the Arabic interface.
@pytest.mark.parametrize(("message", "saved_after", "shown"), [
    ("أنا نباتي وأحب الفطر", {("diet", "vegetarian"), ("like", "mushroom")}, None),
    ("وش تنصحني للعشا أقل من 60 ريال؟", set(), "recommendations"),
    ("عندي حساسية من المكسرات. أي حلى أقدر آكل؟",
     {("allergy", "peanut"), ("allergy", "tree_nut")}, "recommendations"),
    ("قارن بين دجاج بالزبدة و دجاج فيندالو", set(), "comparison"),
])
def test_the_arabic_sample_prompts_work_without_a_model(diner, message, saved_after, shown):
    reply = diner.say(message)
    assert diner.preferences() == saved_after
    payload = reply["payload"]
    if shown:
        assert payload[shown], reply["content"]
    for entry in payload["recommendations"]:
        assert entry["item"]["price"] <= 60 or "60" not in message
    if shown == "comparison":
        assert [e["item"]["id"] for e in payload["comparison"]] == [
            "butter-chicken", "chicken-vindaloo"
        ]


def test_an_unidentified_allergy_of_another_diner_says_how_to_continue(diner):
    reply = diner.say("زوجتي عندها حساسية من الترمس. وش تنصحني لها؟")
    assert picks(reply) == []
    assert "محادثة جديدة" in reply["content"]
    assert "الميزانية" not in reply["content"]
    diner.new_conversation()
    assert picks(diner.say("وش تنصحني للعشا؟"))


def test_naming_an_unidentified_allergy_from_the_list_restores_suggestions(diner):
    diner.say("عندي حساسية من الترمس")
    assert picks(diner.say("recommend a main")) == []
    diner.client.post("/api/memory/allergies", json={"allergen": "peanut"}, headers=diner.headers)
    diner.post(f"/api/memory/{diner.preference_id('allergy', 'الترمس')}/dismiss")
    reply = diner.say("recommend a main")
    assert picks(reply)
    for item in picks(reply):
        assert violations_by_oracle(item, Limits(allergens=("peanut",))) == []


def test_the_interface_labels_every_value_the_server_does():
    source = (ROOT_DIR / "frontend" / "src" / "format.ts").read_text(encoding="utf-8")
    table = source.split("const ARABIC")[1].split("};")[0]
    assert set(re.findall(r"^  (\w+):", table, re.M)) == set(ARABIC_VALUES)
