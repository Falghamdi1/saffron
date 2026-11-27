"""Short-term, per-conversation request state ("today I want something spicy")."""

from app.memory.policy import normalize
from app.schemas import Candidate, RequestConstraints
from app.vocabulary import DIETS, SPICE_LEVELS

GENERIC_NOUNS = {"dish", "dishes", "food", "foods", "meal", "meals", "option", "options"}
NOT_ALLERGENS = {"all", "every", "any", "anything", "something", "nothing", "food"}


def clean(request: RequestConstraints) -> RequestConstraints:
    """Discard values the menu cannot be filtered by, and bound list sizes."""

    def terms(values: list[str]) -> list[str]:
        # "lamb dish" means lamb.
        meant = (
            " ".join(w for w in v.lower().split() if w not in GENERIC_NOUNS)[:40] for v in values
        )
        return list(dict.fromkeys(v for v in meant if v))[:8]

    allergies = [
        canonical.value
        for value in request.allergies if value.strip() and value.lower() not in NOT_ALLERGENS
        for canonical in normalize(Candidate(category="allergy", value=value.strip()[:40]))
    ]

    return request.model_copy(update={
        "allergies": list(dict.fromkeys(allergies))[:16],
        "wants": terms(request.wants),
        "avoid": terms(request.avoid),
        "diets": [d for d in terms(request.diets) if d in DIETS],
        "relaxed_diets": [d for d in terms(request.relaxed_diets) if d in DIETS],
    })


def apply_temporary(
    request: RequestConstraints, stated: list[Candidate]
) -> RequestConstraints:
    """Turn temporary statements into constraints for this conversation."""
    update = request.model_copy(deep=True)
    for candidate in stated:
        if candidate.scope != "temporary" or candidate.category == "allergy":
            continue
        for item in normalize(candidate):
            asserted = item.operation == "assert"
            if item.category == "diet":
                (update.diets if asserted else update.relaxed_diets).append(item.value)
            elif item.category in ("like", "cuisine") and asserted:
                update.wants.append(item.value)
            elif item.category == "dislike" and asserted:
                update.avoid.append(item.value)
            elif item.category == "spice" and asserted:
                update.spice = SPICE_LEVELS.index(item.value)
            elif item.category == "budget" and asserted:
                update.max_price = float(item.value)
    return clean(update)


def merge(
    previous: RequestConstraints, new: RequestConstraints, stated: list[Candidate]
) -> RequestConstraints:
    """Carry constraints across turns, letting newer statements win."""
    new = apply_temporary(new, stated)
    updated = {c.category for c in stated if c.scope == "persistent"}
    spice = None if "spice" in updated else previous.spice
    max_price = None if "budget" in updated else previous.max_price
    new_topic = new.category is not None and new.category != previous.category

    return clean(RequestConstraints(
        category=new.category or (None if new.wants else previous.category),
        wants=new.wants or ([] if new_topic else previous.wants),
        avoid=[*previous.avoid, *new.avoid],
        diets=[*previous.diets, *new.diets],
        relaxed_diets=[*previous.relaxed_diets, *new.relaxed_diets],
        # Table allergies last for the whole conversation, whatever the topic.
        allergies=[*previous.allergies, *new.allergies],
        max_price=new.max_price or max_price,
        spice=new.spice if new.spice is not None else spice,
    ))
