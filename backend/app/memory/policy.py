"""Deterministic rules that decide how a candidate preference changes memory.

This module performs no I/O. It receives a proposed change and the user's current
memory, and returns the operations to apply. Language models only ever propose
candidates; every write is decided here.

Safety invariants:
* An allergy is never removed or weakened by a chat message. A request to remove
  one only flags it, and the user must confirm in the memory panel.
* An uncertain statement never becomes a confirmed allergy or dietary restriction.
* Temporary requests are not persisted. Allergies are always persistent.
* Superseded values are kept, so history is never lost.
"""

import re
from dataclasses import dataclass, field
from typing import Literal

from app import language
from app.i18n import name, say
from app.schemas import Candidate, Certainty, MemoryNote, Preference, Status
from app.vocabulary import (
    CUISINES,
    DIETS,
    EATING_PATTERNS,
    INGREDIENT_GROUPS,
    SPICE_LEVELS,
    allergens_for,
    singular,
)

SINGLE_VALUED = ("spice", "budget")
ANIMAL_FOODS = {"meat", "chicken", "lamb", "beef", "prawn", "fish", "sea bass", "seafood"}
MEAT_FOODS = {"meat", "chicken", "lamb", "beef"}
SPICE_WORDING = re.compile(r"\bspic(?:y|e|es|iness)\b|^heat$")
DIET_ALIASES = {"plant based": "vegan", "veggie": "vegetarian", "lactose free": "dairy_free"}


@dataclass(frozen=True)
class Change:
    action: Literal["create", "update", "flag_removal", "clear_removal"]
    event: str
    reason: str
    category: str
    value: str
    preference_id: str | None = None
    status: Status | None = None
    certainty: Certainty | None = None


@dataclass
class Decision:
    changes: list[Change] = field(default_factory=list)
    notes: list[MemoryNote] = field(default_factory=list)


def describe(category: str, value: str, lang: str = "en") -> str:
    if category == "favorite_dish":
        shown = value.replace("-", " ")
    elif category == "budget":
        shown = value
    else:
        shown = name(value, lang)
    return say(lang, f"d_{category}", value=shown)


def unidentified(value: str) -> bool:
    """An allergy kept in the diner's own script, which no menu data can be checked against."""
    return not value.isascii()


def _from_arabic(category: str, value: str) -> list[str]:
    """Arabic wording as the English terms the rest of the policy understands."""
    folded = language.fold(value).strip()
    if category == "allergy":
        named = [a for group in language.find(folded, language.ALLERGENS) for a in group]
        return named or language.find(folded, language.FOODS) or [value.strip()]
    if category == "budget":
        return [folded.replace("ريال", "").replace("ر.س", "").strip()]
    if category in ("like", "dislike"):
        foods = language.find(folded, language.FOODS)
        if foods or category == "like":
            return foods
        return [a for group in language.find(folded, language.ALLERGENS) for a in group]
    table = {"diet": language.DIETS, "spice": language.SPICE, "cuisine": language.CUISINES}
    return [table[category][folded]] if folded in table.get(category, {}) else []


def normalize(candidate: Candidate) -> list[Candidate]:
    """Map a candidate onto canonical values. Unusable candidates yield []."""
    category = candidate.category
    if category != "favorite_dish" and language.is_arabic(candidate.value):
        results = []
        for term in dict.fromkeys(_from_arabic(category, candidate.value)):
            changed = candidate.model_copy(update={"value": term})
            if category == "allergy" and unidentified(term):
                results.append(changed)
            elif not language.is_arabic(term):
                results += normalize(changed)
        return results
    raw = " ".join(candidate.value.lower().replace("-", " ").split())
    if category == "allergy":
        values = allergens_for(raw) or (singular(raw),)
    elif category == "diet":
        diet = DIET_ALIASES.get(raw, raw.replace(" ", "_"))
        values = (diet,) if diet in DIETS else ()
    elif category == "spice":
        values = (raw,) if raw in SPICE_LEVELS else ()
    elif category == "budget":
        digits = candidate.value.lower().removeprefix("sar").removesuffix("sar").strip()
        try:
            amount = float(digits)
        except ValueError:
            amount = 0
        values = (f"{amount:g}",) if 0 < amount <= 10_000 else ()
    elif category == "cuisine":
        values = (raw,) if raw in CUISINES else ()
    elif category == "favorite_dish":
        values = (candidate.value,)
    else:
        # "Very spicy food" is a spice level, not a food to like or avoid.
        values = () if SPICE_WORDING.search(raw) else (singular(raw),)
    return [candidate.model_copy(update={"value": value}) for value in values]


def decide(candidate: Candidate, memory: list[Preference], lang: str = "en") -> Decision:
    """Decide the effect of one normalized candidate on the current memory."""
    live = [p for p in memory if p.status in ("active", "pending")]
    match = next(
        (p for p in live if p.category == candidate.category and p.value == candidate.value),
        None,
    )
    if candidate.scope == "temporary" and candidate.category != "allergy":
        key = "temporary_use" if candidate.operation == "assert" else "temporary_drop"
        note = say(lang, key, what=describe(candidate.category, candidate.value, lang))
        return Decision(notes=[MemoryNote(kind="temporary", message=note)])
    if candidate.operation == "retract":
        return _retract(candidate, match, lang)
    return _assert(candidate, match, live, lang)


def _retract(candidate: Candidate, match: Preference | None, lang: str) -> Decision:
    if match is None:
        return Decision()
    text = describe(match.category, match.value, lang)
    if match.category == "allergy" or (
        match.category == "diet" and candidate.certainty == "uncertain"
    ):
        change = Change(
            "flag_removal", "removal_requested", "Removal needs explicit confirmation",
            match.category, match.value, match.id,
        )
        note = MemoryNote(
            kind="needs_confirmation",
            message=say(lang, "kept", what=text),
            preference_id=match.id,
        )
        return Decision([change], [note])
    if candidate.certainty == "uncertain":
        return Decision()
    change = Change(
        "update", "retracted", "You said this no longer applies",
        match.category, match.value, match.id, status="retracted",
    )
    return Decision([change], [MemoryNote(kind="removed", message=say(lang, "removed", what=text))])


def _assert(
    candidate: Candidate, match: Preference | None, live: list[Preference], lang: str
) -> Decision:
    category, value = candidate.category, candidate.value
    explicit = candidate.certainty == "explicit"

    conflict = _blocking_conflict(candidate, live, lang)
    if conflict:
        return Decision(notes=[MemoryNote(kind="conflict", message=conflict)])

    decision = Decision()
    text = describe(category, value, lang)

    if match and match.status == "active":
        if match.removal_requested:
            decision.changes.append(Change(
                "clear_removal", "reaffirmed", "You mentioned it again",
                category, value, match.id,
            ))
        else:
            decision.changes.append(Change(
                "update", "reinforced", "You mentioned it again",
                category, value, match.id,
            ))
        return decision

    if category == "allergy" and unidentified(value):
        # Never filter on something that cannot be checked: keep it and ask.
        if match is None:
            decision.changes.append(Change(
                "create", "proposed", "The allergen could not be identified",
                category, value, status="pending", certainty="inferred",
            ))
        decision.notes.append(MemoryNote(
            kind="conflict", message=say(lang, "unidentified", value=value)
        ))
        return decision

    if not explicit:
        if match is None:
            decision.changes.append(Change(
                "create", "proposed", "Inferred from an uncertain statement",
                category, value, status="pending", certainty="inferred",
            ))
        extra = " " + say(lang, "ask_avoid") if category == "allergy" else ""
        decision.notes.append(MemoryNote(
            kind="needs_confirmation",
            message=say(lang, "ask", what=text) + extra,
            preference_id=match.id if match else None,
        ))
        return decision

    replaced = [p for p in live if p is not match and _is_replaced_by(p, category, value)]
    for old in replaced:
        decision.changes.append(Change(
            "update", "superseded", f"Replaced by: {text}",
            old.category, old.value, old.id, status="superseded",
        ))

    if match:
        decision.changes.append(Change(
            "update", "confirmed", "Confirmed by you",
            category, value, match.id, status="active", certainty="confirmed",
        ))
    else:
        decision.changes.append(Change(
            "create", "created", "Stated by you",
            category, value, status="active", certainty="confirmed",
        ))

    if replaced:
        separator = "، " if lang == "ar" else ", "
        previous = separator.join(describe(p.category, p.value, lang) for p in replaced)
        decision.notes.append(MemoryNote(
            kind="updated", message=say(lang, "updated", what=text, previous=previous)
        ))
    else:
        decision.notes.append(MemoryNote(kind="saved", message=say(lang, "saved", what=text)))
    return decision


def _is_replaced_by(old: Preference, category: str, value: str) -> bool:
    """Whether a newly confirmed preference makes an existing one obsolete."""
    if category in SINGLE_VALUED:
        return old.category == category
    if category == "diet" and value in EATING_PATTERNS:
        return old.category == "diet" and old.value in EATING_PATTERNS
    if category == "like":
        return old.category == "dislike" and old.value == value
    if category in ("dislike", "allergy"):
        liked = old.category == "like" and (
            old.value == value or (category == "allergy" and value in allergens_for(old.value))
        )
        return liked
    return False


def _blocking_conflict(
    candidate: Candidate, live: list[Preference], lang: str
) -> str | None:
    """A liked food must not silently contradict an allergy or a diet."""
    if candidate.category != "like":
        return None
    active = [p for p in live if p.status == "active" or p.category == "allergy"]
    allergies = {p.value for p in active if p.category == "allergy"}
    food = candidate.value
    if food in allergies or allergies & set(allergens_for(food)):
        return say(lang, "allergy_conflict", food=name(food, lang))
    diets = {p.value for p in active if p.category == "diet"}
    foods = {food, *INGREDIENT_GROUPS.get(food, ())}
    clashes = (
        (diets & {"vegetarian", "vegan"} and foods & ANIMAL_FOODS)
        or ("pescatarian" in diets and foods & MEAT_FOODS)
    )
    if clashes:
        diet = next(d for d in EATING_PATTERNS if d in diets)
        return say(lang, "diet_conflict", diet=name(diet, lang), food=name(food, lang))
    return None
