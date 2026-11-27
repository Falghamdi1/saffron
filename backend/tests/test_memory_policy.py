"""Memory rules in isolation: no database, no model."""

import pytest

from app.memory.policy import decide, normalize
from app.schemas import Candidate, Preference


def stored(category, value, status="active", **extra):
    return Preference(
        id=f"{category}-{value}", category=category, value=value, status=status,
        certainty="confirmed", **extra,
    )


def candidate(category, value, **extra):
    return Candidate(category=category, value=value, **extra)


def actions(decision):
    return [(c.action, c.event, c.value, c.status) for c in decision.changes]


@pytest.mark.parametrize(("raw", "expected"), [
    ("nuts", {"peanut", "tree_nut"}),
    ("Shellfish", {"crustacean", "mollusc"}),
    ("dairy", {"milk"}),
    ("mango", {"mango"}),
])
def test_allergy_names_are_canonicalised_conservatively(raw, expected):
    assert {c.value for c in normalize(candidate("allergy", raw))} == expected


@pytest.mark.parametrize(("category", "value"), [
    ("diet", "carnivore"), ("spice", "volcanic"), ("budget", "cheap"), ("budget", "-5"),
    ("cuisine", "martian"),
])
def test_values_outside_the_vocabulary_are_dropped(category, value):
    assert normalize(candidate(category, value)) == []


@pytest.mark.parametrize("certainty", ["explicit", "uncertain"])
def test_chat_never_removes_an_allergy(certainty):
    memory = [stored("allergy", "peanut")]
    decision = decide(
        candidate("allergy", "peanut", operation="retract", certainty=certainty), memory
    )
    assert [c.action for c in decision.changes] == ["flag_removal"]
    assert all(c.status is None for c in decision.changes)
    assert decision.notes[0].kind == "needs_confirmation"


def test_uncertain_allergy_is_pending_not_confirmed():
    decision = decide(candidate("allergy", "sesame", certainty="uncertain"), [])
    assert actions(decision) == [("create", "proposed", "sesame", "pending")]
    assert decision.changes[0].certainty == "inferred"


def test_temporary_allergy_statement_is_still_persisted():
    decision = decide(candidate("allergy", "egg", scope="temporary"), [])
    assert actions(decision) == [("create", "created", "egg", "active")]


@pytest.mark.parametrize(("category", "value"), [
    ("diet", "vegan"), ("like", "mushroom"), ("spice", "hot"), ("budget", "90"),
])
def test_temporary_statements_are_not_persisted(category, value):
    decision = decide(candidate(category, value, scope="temporary"), [])
    assert decision.changes == []
    assert decision.notes[0].kind == "temporary"


def test_new_eating_pattern_supersedes_the_old_one_only():
    memory = [stored("diet", "vegetarian"), stored("diet", "gluten_free")]
    decision = decide(candidate("diet", "vegan"), memory)
    assert actions(decision) == [
        ("update", "superseded", "vegetarian", "superseded"),
        ("create", "created", "vegan", "active"),
    ]


def test_budget_is_single_valued():
    decision = decide(candidate("budget", "80"), [stored("budget", "50")])
    assert actions(decision)[0] == ("update", "superseded", "50", "superseded")


def test_dislike_replaces_a_like_of_the_same_food():
    memory = [stored("like", "mushroom"), stored("like", "chicken")]
    decision = decide(candidate("dislike", "mushroom"), memory)
    assert [c.value for c in decision.changes if c.status == "superseded"] == ["mushroom"]


def test_uncertain_conflicting_statement_leaves_confirmed_memory_untouched():
    decision = decide(
        candidate("dislike", "mushroom", certainty="uncertain"), [stored("like", "mushroom")]
    )
    assert actions(decision) == [("create", "proposed", "mushroom", "pending")]


def test_liking_an_allergen_is_refused():
    decision = decide(candidate("like", "peanut"), [stored("allergy", "peanut")])
    assert decision.changes == []
    assert decision.notes[0].kind == "conflict"


def test_liking_meat_does_not_overwrite_a_vegetarian_diet():
    decision = decide(candidate("like", "chicken"), [stored("diet", "vegetarian")])
    assert decision.changes == []
    assert "no longer vegetarian" in decision.notes[0].message


def test_repeating_a_preference_reinforces_it():
    decision = decide(candidate("like", "mint"), [stored("like", "mint")])
    assert actions(decision) == [("update", "reinforced", "mint", None)]


def test_confirming_a_pending_preference_activates_it():
    memory = [stored("diet", "vegetarian", status="pending")]
    decision = decide(candidate("diet", "vegetarian"), memory)
    assert actions(decision) == [("update", "confirmed", "vegetarian", "active")]


@pytest.mark.parametrize(("phrase", "allergens"), [
    ("sesame seeds", {"sesame"}),
    ("peanut butter", {"peanut"}),
    ("egg whites", {"egg"}),
    ("pine nuts", {"tree_nut"}),
    ("coconut", {"coconut"}),
])
def test_multi_word_allergies_resolve_to_tracked_allergens(phrase, allergens):
    assert {c.value for c in normalize(candidate("allergy", phrase))} == allergens
