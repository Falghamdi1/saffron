"""Rule extraction, the Gemini adapter and model/rule reconciliation."""

import json

import httpx
import pytest

from app.schemas import Candidate, Understanding
from app.understanding.llm import GeminiProvider, LLMError, response_schema
from app.understanding.rules import understand as rules
from app.understanding.service import understand


def found(message):
    return {
        (c.category, c.value, c.operation, c.scope, c.certainty)
        for c in rules(message).preferences
    }


@pytest.mark.parametrize(("message", "expected"), [
    ("I'm allergic to peanuts", ("allergy", "peanut", "assert", "persistent", "explicit")),
    ("I think I might be allergic to sesame",
     ("allergy", "sesame", "assert", "persistent", "uncertain")),
    ("I'm not allergic to peanuts anymore",
     ("allergy", "peanut", "retract", "persistent", "explicit")),
    ("I don't have a nut allergy", ("allergy", "nut", "retract", "persistent", "explicit")),
    ("I'm no longer vegetarian", ("diet", "vegetarian", "retract", "persistent", "explicit")),
    ("I don't eat much meat", ("diet", "vegetarian", "assert", "persistent", "uncertain")),
    ("I think I might be vegetarian", ("diet", "vegetarian", "assert", "persistent", "uncertain")),
    ("I really love mushrooms", ("like", "mushroom", "assert", "persistent", "explicit")),
    ("My budget is 60 SAR", ("budget", "60", "assert", "persistent", "explicit")),
    ("I can't handle spicy food", ("spice", "none", "assert", "persistent", "explicit")),
])
def test_rules_extract_preferences(message, expected):
    assert expected in found(message)


@pytest.mark.parametrize("message", [
    "Today I want something spicy",
    "something under 40 SAR with chicken",
    "I don't like to wait",
    "I am allergic to nothing",
    "My friend is allergic to peanuts",
])
def test_rules_do_not_invent_lasting_preferences(message):
    assert rules(message).preferences == []


def test_request_constraints_are_separate_from_memory():
    result = rules("something under 40 SAR with chicken")
    assert result.request.max_price == 40
    assert result.request.wants == ["chicken"]


def gemini(handler):
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return GeminiProvider("test-key", "test-model", client=client)


def reply_with(payload: dict):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["x-goog-api-key"] == "test-key"
        assert "test-key" not in str(request.url)
        return httpx.Response(200, json={"steps": [
            {"type": "model_output", "content": [{"type": "text", "text": json.dumps(payload)}]}
        ]})

    return handler


def test_gemini_response_is_parsed_and_validated():
    result = gemini(reply_with({"intent": "recommend"})).understand("hungry")
    assert result.intent == "recommend"


@pytest.mark.parametrize("handler", [
    lambda request: httpx.Response(429, json={"error": "quota"}),
    lambda request: httpx.Response(200, json={"steps": []}),
    lambda request: httpx.Response(200, text="not json"),
    reply_with({"intent": "order_everything"}),
])
def test_gemini_failures_raise_one_error_type(handler):
    with pytest.raises(LLMError):
        gemini(handler).understand("hello")


class FakeProvider:
    name = "fake"

    def __init__(self, result=None):
        self.result = result

    def understand(self, message):
        if self.result is None:
            raise LLMError("down")
        return self.result


def test_model_failure_falls_back_to_rules():
    result, engine = understand("I'm allergic to eggs", FakeProvider())
    assert engine == "fallback"
    assert result.preferences[0].value == "egg"


def test_allergy_missed_by_the_model_is_still_captured():
    result, _ = understand("I'm allergic to eggs, what's for lunch?", FakeProvider(Understanding()))
    assert [(c.category, c.value) for c in result.preferences] == [("allergy", "egg")]


def test_preference_the_model_cannot_quote_is_discarded():
    invented = Understanding(preferences=[
        Candidate(category="diet", value="vegan", evidence="I am vegan"),
        Candidate(category="like", value="mint", evidence="I love mint"),
    ])
    result, _ = understand("I love mint", FakeProvider(invented))
    assert [c.value for c in result.preferences] == ["mint"]


def test_hedged_diet_cannot_be_upgraded_by_the_model():
    sure = Understanding(preferences=[
        Candidate(category="diet", value="vegetarian", evidence="I don't eat much meat")
    ])
    result, _ = understand("I don't eat much meat", FakeProvider(sure))
    assert result.preferences[0].certainty == "uncertain"


def test_model_cannot_invent_a_favourite_dish():
    invented = Understanding(preferences=[
        Candidate(category="favorite_dish", value="sushi", evidence="sushi")
    ])
    result, _ = understand("sushi", FakeProvider(invented))
    assert result.preferences == []


def test_gemini_schema_requires_the_fields_the_pipeline_depends_on():
    schema = response_schema()
    assert "evidence" in schema["properties"]["preferences"]["items"]["required"]


def test_gemini_schema_uses_only_the_documented_subset():
    schema = response_schema()
    text = json.dumps(schema)
    for keyword in ("$ref", "$defs", "anyOf", "default", "exclusiveMinimum", "maxLength"):
        assert f'"{keyword}"' not in text
    request = schema["properties"]["request"]["properties"]
    assert request["max_price"]["type"] == ["number", "null"]
    assert None in request["category"]["enum"]


def test_zero_budget_from_a_model_means_no_budget():
    assert Understanding(request={"max_price": 0}).request.max_price is None


def test_price_limit_missed_by_the_model_is_restored():
    result, _ = understand("dinner under 60 riyals", FakeProvider(Understanding()))
    assert result.request.max_price == 60


@pytest.mark.parametrize("message", [
    "I don't eat much meat", "I rarely eat meat", "I'm not really into meat",
])
def test_softened_statements_from_the_model_stay_unconfirmed(message):
    firm = Understanding(preferences=[
        Candidate(category="dislike", value="meat", evidence=message)
    ])
    result, _ = understand(message, FakeProvider(firm))
    assert {c.certainty for c in result.preferences} == {"uncertain"}


def test_firm_dislikes_are_not_softened():
    message = "I really don't like mushrooms"
    firm = Understanding(preferences=[
        Candidate(category="dislike", value="mushroom", evidence=message)
    ])
    result, _ = understand(message, FakeProvider(firm))
    assert result.preferences[0].certainty == "explicit"


def test_a_brief_overload_is_retried_once():
    statuses = [503, 200]

    def handler(request):
        if statuses.pop(0) == 503:
            return httpx.Response(503)
        return reply_with({"intent": "greeting"})(request)

    assert gemini(handler).understand("hi").intent == "greeting"
