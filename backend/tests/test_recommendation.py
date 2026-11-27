"""Menu data integrity and recommender behaviour."""

import itertools

import pytest

from app.recommendation.dishes import mentioned
from app.recommendation.engine import Profile, recommend
from app.vocabulary import ALLERGENS, CATEGORIES, CUISINES, DIETS

ANIMAL = {"chicken", "lamb", "prawns", "sea bass"}


def ids(result):
    return [r.item.id for r in result.recommendations]


def test_menu_meets_the_brief(menu):
    assert len(menu) >= 12
    assert len({i.category for i in menu}) >= 3
    assert {i.spice_level for i in menu} == {0, 1, 2, 3}
    assert len({i.id for i in menu}) == len(menu)
    assert all(i.category in CATEGORIES and i.cuisine in CUISINES for i in menu)


def test_menu_labels_are_consistent_with_ingredients(menu):
    """A wrong diet tag would defeat filtering, so the data itself is tested."""
    for item in menu:
        assert set(item.allergens) | set(item.may_contain) <= set(ALLERGENS), item.id
        assert set(item.diets) <= set(DIETS), item.id
        if {"vegetarian", "vegan"} & set(item.diets):
            assert not ANIMAL & set(item.ingredients), item.id
        if "vegan" in item.diets:
            assert not {"milk", "egg"} & set(item.allergens), item.id
            assert "honey" not in item.ingredients, item.id
        if "dairy_free" in item.diets:
            assert "milk" not in item.allergens, item.id
        if "gluten_free" in item.diets:
            assert "gluten" not in item.allergens, item.id


@pytest.mark.parametrize("allergies", [
    set(pair) for size in (1, 2) for pair in itertools.combinations(ALLERGENS, size)
])
def test_no_ranking_can_surface_an_allergen(menu, allergies):
    # Every preference points at as many dishes as possible, to tempt the ranker.
    profile = Profile(
        allergies=frozenset(allergies),
        likes=frozenset({"chicken", "cheese", "nut", "chickpea"}),
        cuisines=frozenset(CUISINES),
        favorites=frozenset(i.id for i in menu),
    )
    for item in (r.item for r in recommend(menu, profile, limit=100).recommendations):
        assert not allergies & (set(item.allergens) | set(item.may_contain))
        assert item.allergen_info_complete
        assert item.available


def test_budget_and_diet_are_hard_limits(menu):
    result = recommend(menu, Profile(diets=frozenset({"vegan"}), max_price=30), limit=100)
    assert ids(result)
    assert all("vegan" in r.item.diets and r.item.price <= 30 for r in result.recommendations)


def test_spice_preference_changes_ranking_without_excluding(menu):
    mild = recommend(menu, Profile(category="main", spice=0), limit=100)
    hot = recommend(menu, Profile(category="main", spice=3), limit=100)
    assert mild.recommendations[0].item.spice_level == 0
    assert hot.recommendations[0].item.spice_level == 3
    assert sorted(ids(mild)) == sorted(ids(hot))


def test_liked_ingredient_ranks_first(menu):
    result = recommend(menu, Profile(category="main", likes=frozenset({"paneer"})))
    assert ids(result)[0] == "paneer-tikka"
    assert any("paneer" in reason for reason in result.recommendations[0].reasons)


def test_unavailable_dish_is_never_recommended(menu):
    result = recommend(menu, Profile(category="dessert"), limit=100)
    assert "pistachio-ice-cream" not in ids(result)
    assert any(e.item_id == "pistachio-ice-cream" for e in result.excluded)


def test_incomplete_allergen_data_is_excluded_for_allergic_users_only(menu):
    without = recommend(menu, Profile(category="main"), limit=100)
    with_allergy = recommend(
        menu, Profile(category="main", allergies=frozenset({"fish"})), limit=100
    )
    assert "chef-special-stew" in ids(without)
    assert "chef-special-stew" not in ids(with_allergy)


def test_unsatisfiable_request_returns_nothing_rather_than_relaxing_rules(menu):
    result = recommend(menu, Profile(diets=frozenset({"vegan"}), max_price=1))
    assert result.recommendations == []


def test_unmatched_food_request_is_reported(menu):
    result = recommend(menu, Profile(wants=("sushi",)))
    assert result.unmatched_wants == ["sushi"]


@pytest.mark.parametrize(("message", "expected"), [
    ("compare butter chicken and the vindaloo", ["butter-chicken", "chicken-vindaloo"]),
    ("what's in the kunafa?", ["kunafa"]),
    ("something with halloumi and pistachio please", []),
    ("do you have sushi", []),
])
def test_dish_mentions(menu, message, expected):
    assert [i.id for i in mentioned(message, menu)] == expected


def test_disliking_one_dairy_food_does_not_exclude_all_dairy(menu):
    cheese = ids(recommend(menu, Profile(dislikes=frozenset({"cheese"})), limit=100))
    dairy = ids(recommend(menu, Profile(dislikes=frozenset({"dairy"})), limit=100))
    assert "butter-chicken" in cheese and "halloumi-skewers" not in cheese
    assert "butter-chicken" not in dairy
