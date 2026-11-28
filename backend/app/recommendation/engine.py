"""Menu recommendation: hard exclusions first, then ranking of what remains.

Pure functions over menu records. Ranking only ever sees items that passed every
hard constraint, so no score can outweigh an allergy, diet, budget or stock rule.
"""

from dataclasses import dataclass, field

from app.memory.policy import unidentified
from app.schemas import Exclusion, MenuItem, Preference, Recommendation, RequestConstraints
from app.vocabulary import (
    ALLERGEN_CLASSES,
    ALLERGENS,
    INGREDIENT_GROUPS,
    SPICE_LEVELS,
    allergens_for,
    label,
    singular,
)


@dataclass(frozen=True)
class Profile:
    """The effective constraints for one request: memory merged with the request."""

    allergies: frozenset[str] = frozenset()
    unconfirmed_allergies: frozenset[str] = frozenset()
    diets: frozenset[str] = frozenset()
    dislikes: frozenset[str] = frozenset()
    likes: frozenset[str] = frozenset()
    soft_diets: frozenset[str] = frozenset()
    cuisines: frozenset[str] = frozenset()
    favorites: frozenset[str] = frozenset()
    spice: int | None = None
    max_price: float | None = None
    category: str | None = None
    wants: tuple[str, ...] = field(default=())


def build_profile(memory: list[Preference], request: RequestConstraints) -> Profile:
    active = [p for p in memory if p.status == "active"]

    def values(category: str) -> set[str]:
        return {p.value for p in active if p.category == category}

    # Allergies awaiting confirmation are still excluded, as a precaution.
    unconfirmed = {
        p.value for p in memory if p.category == "allergy" and p.status == "pending"
    }
    pending_diets = {p.value for p in memory if p.category == "diet" and p.status == "pending"}

    stored_diets = values("diet") - set(request.relaxed_diets)
    spice = next((SPICE_LEVELS.index(v) for v in values("spice")), None)
    budget = next((float(v) for v in values("budget")), None)
    wants = tuple(singular(w) for w in request.wants)

    return Profile(
        allergies=frozenset(values("allergy") | set(request.allergies)),
        unconfirmed_allergies=frozenset(unconfirmed),
        diets=frozenset(stored_diets | set(request.diets)),
        # Asking for a normally disliked food lifts the dislike for this chat only.
        dislikes=frozenset(
            (values("dislike") - set(wants)) | {singular(a) for a in request.avoid}
        ),
        likes=frozenset(values("like")),
        soft_diets=frozenset(pending_diets),
        cuisines=frozenset(values("cuisine")),
        favorites=frozenset(values("favorite_dish")),
        spice=request.spice if request.spice is not None else spice,
        max_price=request.max_price or budget,
        category=request.category,
        wants=wants,
    )


def matches_food(item: MenuItem, term: str) -> bool:
    """Whether a food word refers to this item, its ingredients or its allergens."""
    term = singular(term)
    if term in (item.cuisine, item.category):
        return True
    haystack = " | ".join([item.name, *item.ingredients]).lower()
    words = f" {' '.join(singular(w) for w in haystack.replace('|', ' | ').split())} "
    for needle in (term, *INGREDIENT_GROUPS.get(term, ())):
        if f" {singular(needle)} " in words:
            return True
    return False


def violations(item: MenuItem, profile: Profile) -> list[str]:
    """Every hard constraint this item breaks. An empty list means it is eligible."""
    found: list[str] = []
    if not item.available:
        found.append("currently unavailable")

    allergies = profile.allergies | profile.unconfirmed_allergies
    for allergy in sorted(allergies):
        if unidentified(allergy):
            found.append("an allergy has not been identified")
        elif allergy in ALLERGENS:
            if allergy in item.allergens:
                found.append(f"contains {label(allergy)}")
            elif allergy in item.may_contain:
                found.append(f"may contain {label(allergy)}")
        elif matches_food(item, allergy):
            found.append(f"contains {allergy}")
    if allergies and not item.allergen_info_complete:
        found.append("allergen information is incomplete")

    for diet in sorted(profile.diets):
        if diet not in item.diets:
            found.append(f"not {label(diet)}")
        elif diet == "gluten_free" and "gluten" in item.may_contain:
            found.append("may contain gluten")

    for food in sorted(profile.dislikes):
        covered = allergens_for(food) if food in ALLERGEN_CLASSES else ()
        if matches_food(item, food) or set(covered) & set(item.allergens):
            found.append(f"includes {food}, which you avoid")

    if profile.max_price is not None and item.price > profile.max_price:
        found.append(f"SAR {item.price:g} is over your SAR {profile.max_price:g} budget")
    return found


def _score(item: MenuItem, profile: Profile) -> tuple[float, list[str]]:
    score = 0.0
    reasons: list[str] = []

    for want in profile.wants:
        if matches_food(item, want):
            score += 5
            reasons.append(f"Matches your request for {want}")

    liked = sorted(food for food in profile.likes if matches_food(item, food))
    if liked:
        score += 3 * len(liked)
        reasons.append(f"Features {', '.join(liked)}, which you like")

    if item.id in profile.favorites:
        score += 3
        reasons.append("One of your saved favourites")

    if item.cuisine in profile.cuisines:
        score += 2
        reasons.append(f"{item.cuisine.title()} cuisine, which you enjoy")

    for diet in sorted(profile.soft_diets):
        if diet in item.diets:
            score += 1

    if profile.spice is not None:
        gap = item.spice_level - profile.spice
        # Too hot is worse than too mild, unless the user is asking for heat.
        score -= 2.5 * gap if gap > 0 else -gap * (1.5 if profile.spice >= 2 else 0.25)
        if gap == 0:
            reasons.append(f"Spice level is {SPICE_LEVELS[item.spice_level]}, as you prefer")

    if item.category == "main":
        score += 0.75

    if profile.diets:
        reasons.append(
            "Meets your " + " and ".join(label(d) for d in sorted(profile.diets)) + " requirement"
        )
    if profile.max_price is not None:
        reasons.append(f"SAR {item.price:g}, within your SAR {profile.max_price:g} budget")
    allergies = sorted(profile.allergies | profile.unconfirmed_allergies)
    if allergies:
        *rest, last = [label(a) for a in allergies]
        named = f"{', '.join(rest)} or {last}" if rest else last
        reasons.append(f"No {named} listed in its recorded ingredients")
    if not reasons:
        reasons.append(item.description)
    return score, reasons


def _cautions(item: MenuItem, profile: Profile) -> list[str]:
    cautions = []
    if not item.allergen_info_complete:
        cautions.append("Allergen information for this dish is incomplete.")
    if profile.spice is not None and item.spice_level > profile.spice:
        cautions.append("Spicier than you usually like.")
    return cautions


@dataclass
class Result:
    recommendations: list[Recommendation]
    excluded: list[Exclusion]
    unmatched_wants: list[str]


def recommend(items: list[MenuItem], profile: Profile, limit: int = 3) -> Result:
    pool = [i for i in items if profile.category in (None, i.category)]
    eligible: list[MenuItem] = []
    excluded: list[Exclusion] = []
    for item in pool:
        problems = violations(item, profile)
        if problems:
            excluded.append(Exclusion(item_id=item.id, name=item.name, reasons=problems))
        else:
            eligible.append(item)

    # A requested food narrows the list when it can; otherwise say it could not.
    unmatched = [w for w in profile.wants if not any(matches_food(i, w) for i in eligible)]
    matched = [w for w in profile.wants if w not in unmatched]
    if matched:
        eligible = [i for i in eligible if any(matches_food(i, w) for w in matched)]

    ranked = []
    for item in eligible:
        score, reasons = _score(item, profile)
        ranked.append(Recommendation(
            item=item, score=score, reasons=reasons, cautions=_cautions(item, profile)
        ))
    ranked.sort(key=lambda r: (-r.score, r.item.price, r.item.name))
    return Result(ranked[:limit], excluded, unmatched)
