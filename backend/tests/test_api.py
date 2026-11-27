"""End-to-end behaviour through the HTTP API against a real database."""

import json
import time

import jwt
import psycopg
import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.schemas import Understanding
from app.understanding.llm import LLMError
from evaluation.harness import Diner, picks

USER_TABLES = ("profiles", "conversations", "messages", "preferences", "memory_events")


def test_health_reports_menu(client):
    assert client.get("/api/health").json() == {"status": "ok", "menu_items": 24}


@pytest.mark.parametrize("path", ["/api/memory", "/api/conversations", "/api/menu"])
def test_routes_require_a_token(client, path):
    assert client.get(path).status_code == 401


def test_forged_and_expired_tokens_are_rejected(client, settings):
    claims = {
        "sub": "00000000-0000-0000-0000-000000000001", "role": "authenticated",
        "aud": "authenticated", "iss": "saffron-local", "exp": int(time.time()) + 600,
    }
    forged = jwt.encode(claims, "a-different-secret-of-sufficient-length", "HS256")
    expired = jwt.encode({**claims, "exp": 1}, settings.local_jwt_secret, "HS256")
    unsigned = jwt.encode(claims, None, "none")
    for token in (forged, expired, unsigned, "rubbish"):
        response = client.get("/api/memory", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 401


@pytest.mark.parametrize("url", [
    "postgresql://u:p@db.example.com/x",
    "postgresql://u:p@localhost/x?host=db.example.com",
    "postgresql://u:p@localhost/x?hostaddr=203.0.113.5",
    "postgresql://u:p@localhost,db.example.com/x",
    "postgresql:///x",
    "not a url",
])
def test_local_sign_in_refuses_a_remote_database(url):
    with pytest.raises(ValueError, match="only works with a database on this machine"):
        Settings(_env_file=None, auth_mode="local", database_url=url)


@pytest.mark.parametrize("url", [
    "postgresql://postgres:@127.0.0.1:5432/postgres",
    "postgresql://postgres:@/postgres?host=/tmp/pg",  # pgserver on Linux and macOS
])
def test_local_sign_in_accepts_a_database_on_this_machine(url):
    assert Settings(_env_file=None, auth_mode="local", database_url=url).database_url == url


def test_blank_and_oversized_messages_are_rejected(diner):
    for message in ("   ", "x" * 1001):
        response = diner.client.post(
            "/api/chat", json={"message": message}, headers=diner.headers
        )
        assert response.status_code == 422


def test_memory_persists_into_a_new_conversation(diner):
    diner.say("I'm vegetarian and I love paneer")
    diner.new_conversation()
    reply = diner.say("What should I have for a main?")
    assert picks(reply)[0] == "paneer-tikka"
    assert all("vegetarian" in r["item"]["diets"] for r in reply["payload"]["recommendations"])


def top_spice(message):
    return message["payload"]["recommendations"][0]["item"]["spice_level"]


def test_temporary_request_stays_in_its_conversation(diner):
    diner.say("I usually prefer mild food")
    diner.say("Today I want something spicy for a main")
    assert top_spice(diner.say("recommend a main")) == 3
    diner.new_conversation()
    assert top_spice(diner.say("recommend a main")) == 1
    assert ("spice", "mild") in diner.preferences()


def test_temporary_diet_relaxation_does_not_change_memory(diner):
    diner.say("I'm vegetarian")
    reply = diner.say("I'm not vegetarian today, recommend a main with lamb")
    assert "lamb-kabsa" in picks(reply)
    assert ("diet", "vegetarian") in diner.preferences()


def test_allergy_removal_needs_confirmation_in_the_panel(diner):
    diner.say("I'm allergic to peanuts and I love mint")
    diner.say("I'm not allergic to peanuts anymore")
    assert ("allergy", "peanut") in diner.preferences()
    pending_removal = next(
        p for p in diner.memory()["preferences"] if p["category"] == "allergy"
    )
    assert pending_removal["removal_requested"]
    response = diner.client.post(
        f"/api/memory/{pending_removal['id']}/confirm", headers=diner.headers
    )
    assert response.status_code == 200
    assert diner.preferences() == {("like", "mint")}
    events = [e["event_type"] for e in diner.memory()["history"]]
    assert events.count("removal_requested") == 1 and "retracted" in events


def test_unconfirmed_allergy_is_excluded_as_a_precaution(diner):
    diner.say("I think I might be allergic to sesame")
    assert diner.preferences("pending") == {("allergy", "sesame")}
    reply = diner.say("recommend a starter")
    for recommendation in reply["payload"]["recommendations"]:
        item = recommendation["item"]
        assert "sesame" not in item["allergens"] + item["may_contain"]


def test_dismissing_a_suggestion_removes_it(diner):
    diner.say("Maybe I'm vegetarian")
    preference_id = diner.preference_id("diet", "vegetarian")
    diner.client.post(f"/api/memory/{preference_id}/dismiss", headers=diner.headers)
    assert diner.memory()["preferences"] == []


def test_correction_keeps_history_and_unrelated_preferences(diner):
    diner.say("My budget is 50 and I love chicken")
    diner.say("Actually my budget is 90")
    assert diner.preferences() == {("budget", "90"), ("like", "chicken")}
    history = diner.memory()["history"]
    assert any(e["event_type"] == "superseded" and e["value"] == "50" for e in history)


def test_cheaper_follow_up_stays_in_the_same_course(diner):
    first = diner.say("recommend a main with lamb")
    second = diner.say("something cheaper")
    lowest = min(r["item"]["price"] for r in first["payload"]["recommendations"])
    assert second["payload"]["recommendations"]
    for recommendation in second["payload"]["recommendations"]:
        assert recommendation["item"]["category"] == "main"
        assert recommendation["item"]["price"] < lowest


def test_nonexistent_dish_is_not_invented(diner):
    reply = diner.say("Do you have sushi?")
    assert "isn't on our menu" in reply["content"]
    assert "sushi" not in json.dumps(reply["payload"]["recommendations"]).lower()


def test_dish_question_flags_the_users_allergy(diner):
    diner.say("I'm allergic to nuts")
    reply = diner.say("What's in the kunafa?")
    assert "I don't recommend it for you" in reply["content"]
    assert reply["payload"]["comparison"][0]["violations"] == ["contains tree nuts"]
    assert "cross-contact" in reply["payload"]["notice"]


def test_menu_marks_conflicts_for_the_signed_in_user(diner):
    diner.say("I'm allergic to dairy")
    items = {i["id"]: i for i in diner.get("/api/menu").json()}
    assert "contains dairy" in items["kunafa"]["violations"]
    assert items["mango-sorbet"]["violations"] == []


def test_favourite_dish_is_remembered(diner):
    response = diner.client.post("/api/favorites/falafel-bowl", headers=diner.headers)
    assert response.status_code == 200
    assert ("favorite_dish", "falafel-bowl") in diner.preferences()
    missing = diner.client.post("/api/favorites/sushi", headers=diner.headers)
    assert missing.status_code == 404


def test_conversations_can_be_reopened(diner):
    diner.say("recommend a dessert")
    listed = diner.get("/api/conversations").json()
    assert [c["id"] for c in listed] == [diner.conversation_id]
    messages = diner.get(f"/api/conversations/{diner.conversation_id}/messages").json()
    assert [m["role"] for m in messages] == ["user", "assistant"]
    assert messages[1]["payload"]["recommendations"]


def test_allergy_can_be_recorded_without_language_understanding(diner):
    response = diner.client.post(
        "/api/memory/allergies", json={"allergen": "tree_nut"}, headers=diner.headers
    )
    assert response.status_code == 200
    assert diner.preferences() == {("allergy", "tree_nut")}
    invalid = diner.client.post(
        "/api/memory/allergies", json={"allergen": "kryptonite"}, headers=diner.headers
    )
    assert invalid.status_code == 422


def test_users_cannot_see_or_change_each_others_data(client):
    alice, bob = Diner(client), Diner(client)
    alice.say("I'm allergic to eggs")
    alice_preference = alice.preference_id("allergy", "egg")

    assert bob.memory() == {"preferences": [], "history": []}
    assert bob.get("/api/conversations").json() == []
    assert bob.get(f"/api/conversations/{alice.conversation_id}/messages").status_code == 404
    intrude = bob.client.post(
        "/api/chat",
        json={"message": "hello", "conversation_id": alice.conversation_id},
        headers=bob.headers,
    )
    assert intrude.status_code == 404
    for method, path in (
        ("delete", f"/api/memory/{alice_preference}"),
        ("post", f"/api/memory/{alice_preference}/confirm"),
        ("post", f"/api/memory/{alice_preference}/dismiss"),
    ):
        assert getattr(bob.client, method)(path, headers=bob.headers).status_code == 404
    assert ("allergy", "egg") in alice.preferences()


def test_row_level_security_blocks_unfiltered_queries(client, admin):
    """Even a query with no user filter must only see the session user's rows."""
    alice, bob = Diner(client), Diner(client)
    alice.say("I'm allergic to eggs")
    bob.say("I love mint")
    database = client.app.state.database
    bob_id = _user_id(admin, bob)
    alice_id = _user_id(admin, alice)

    with database.user_session(bob_id) as connection:
        for table in USER_TABLES:
            column = "id" if table == "profiles" else "user_id"
            owners = connection.execute(f"select distinct {column}::text as o from app.{table}")
            assert {row["o"] for row in owners} == {bob_id}, table
        updated = connection.execute(
            "update app.preferences set status = 'retracted' where user_id = %s", (alice_id,)
        )
        assert updated.rowcount == 0

    with pytest.raises(psycopg.errors.InsufficientPrivilege), \
            database.user_session(bob_id) as connection:
        connection.execute(
            "insert into app.preferences (user_id, category, value, status, certainty) "
            "values (%s, 'like', 'x', 'active', 'confirmed')",
            (alice_id,),
        )
    with pytest.raises(psycopg.errors.ForeignKeyViolation), \
            database.user_session(bob_id) as connection:
        connection.execute(
            "insert into app.messages (conversation_id, user_id, role, content) "
            "values (%s, %s, 'user', 'x')",
            (alice.conversation_id, bob_id),
        )


@pytest.mark.parametrize("statement", [
    "delete from app.memory_events",
    "update app.memory_events set reason = 'x'",
    "delete from app.preferences",
])
def test_history_cannot_be_rewritten(client, admin, statement):
    user = Diner(client)
    user.say("I love mint")
    with pytest.raises(psycopg.errors.InsufficientPrivilege), \
            client.app.state.database.user_session(_user_id(admin, user)) as connection:
        connection.execute(statement)


def _user_id(admin, diner: Diner) -> str:
    return admin.execute(
        "select id::text from app.profiles where display_name = %s", (diner.name,)
    ).fetchone()[0]


class BrokenProvider:
    name = "broken"

    def understand(self, message):
        raise LLMError("simulated outage")


def test_chat_keeps_working_when_the_model_fails(settings):
    with TestClient(create_app(settings, provider=BrokenProvider())) as client:
        diner = Diner(client)
        reply = diner.say("I'm allergic to fish. Recommend a main")
        assert reply["payload"]["engine"] == "fallback"
        assert picks(reply)
        assert "sea-bass" not in picks(reply)


def test_chat_is_rate_limited(settings):
    limited = settings.model_copy(update={"chat_rate_limit_per_minute": 2})
    with TestClient(create_app(limited)) as client:
        diner = Diner(client)
        diner.say("hello")
        diner.say("hello")
        response = client.post("/api/chat", json={"message": "hi"}, headers=diner.headers)
        assert response.status_code == 429


class DishAsFoodProvider:
    """Mimics a model that lists an unknown dish both as a name and as a wanted food."""

    name = "gemini"

    def understand(self, message):
        return Understanding(
            intent="dish_question", dish_names=["sushi"], request={"wants": ["sushi"]}
        )


def test_unknown_dish_is_reported_when_the_model_also_calls_it_a_food(settings):
    with TestClient(create_app(settings, provider=DishAsFoodProvider())) as client:
        reply = Diner(client).say("Do you have sushi?")
        assert "isn't on our menu" in reply["content"]
        assert "couldn't find" not in reply["content"]
        assert picks(reply)


def test_pasted_environment_values_are_trimmed(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@127.0.0.1/x?sslmode=require\n")
    monkeypatch.setenv("GEMINI_API_KEY", "  not-a-real-key\n")
    settings = Settings(_env_file=None, auth_mode="local")
    assert settings.database_url.endswith("sslmode=require")
    assert settings.gemini_api_key == "not-a-real-key"


class Scripted:
    """A model double that answers each message with a prepared understanding."""

    name = "scripted"

    def __init__(self, replies):
        self.replies = replies

    def understand(self, message):
        return Understanding(**self.replies.get(message, {}))


def test_a_dish_question_does_not_shape_the_next_request(settings):
    script = Scripted({
        "Can I get the pistachio ice cream?": {
            "intent": "dish_question",
            "request": {"category": "dessert", "wants": ["pistachio ice cream"]},
        },
        "Recommend a dessert": {"intent": "recommend", "request": {"category": "dessert"}},
    })
    with TestClient(create_app(settings, provider=script)) as client:
        diner = Diner(client)
        diner.say("Can I get the pistachio ice cream?")
        reply = diner.say("Recommend a dessert")
        assert "couldn't find" not in reply["content"]
        assert picks(reply)
