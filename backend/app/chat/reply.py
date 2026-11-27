"""Compose the assistant's text.

Every dish name, price and allergen fact here is copied from menu records chosen by
the recommender. No language model writes this text, so it cannot invent a dish.
"""

from app.recommendation.engine import Profile
from app.schemas import Exclusion, MemoryNote, MenuItem
from app.vocabulary import ALLERGENS, label

HELP = (
    "Tell me what you feel like eating, anything you can't have, or a budget. "
    "You can also ask me to compare two dishes."
)


def _join(parts: list[str]) -> str:
    return parts[0] if len(parts) == 1 else f"{', '.join(parts[:-1])} and {parts[-1]}"


def safety_notice(profile: Profile) -> str:
    allergies = sorted(profile.allergies | profile.unconfirmed_allergies)
    if not allergies:
        return ""
    notice = (
        f"Checked against recorded ingredient and “may contain” data for "
        f"{_join([label(a) for a in allergies])}. This cannot rule out cross-contact in the "
        "kitchen, so please tell your server about your allergy."
    )
    untracked = [a for a in allergies if a not in ALLERGENS]
    if untracked:
        notice += (
            f" {_join(untracked).capitalize()} is not a formally tracked allergen here: only "
            "ingredient names were checked."
        )
    return notice


def acknowledgement(notes: list[MemoryNote]) -> str:
    return " ".join(note.message for note in notes)


def recommendations(
    names: list[str], excluded: list[Exclusion], unmatched: list[str], cheaper: bool
) -> str:
    parts = []
    if unmatched:
        parts.append(f"I couldn't find an option with {_join(unmatched)} that fits.")
    if not names:
        parts.append(
            "Nothing cheaper fits your requirements." if cheaper else
            "Nothing on the menu meets all of your requirements right now. "
            "I won't relax an allergy or diet, but you could raise the budget or change the course."
        )
        return " ".join(parts)
    lead = "Here is" if len(names) == 1 else "Here are"
    parts.append(f"{lead} {_join(names)}.")
    if excluded:
        count = len(excluded)
        parts.append(
            f"I left out {count} dish{'es' if count > 1 else ''} that "
            f"{'break' if count > 1 else 'breaks'} one of your requirements."
        )
    return " ".join(parts)


def dish_facts(checked: list[tuple[MenuItem, list[str]]]) -> str:
    sentences = []
    for item, problems in checked:
        listed = _join([label(a) for a in item.allergens]) if item.allergens else "none recorded"
        sentence = (
            f"{item.name} is SAR {item.price:g}. Ingredients: {', '.join(item.ingredients)}. "
            f"Allergens: {listed}."
        )
        if item.may_contain:
            sentence += f" May contain {_join([label(a) for a in item.may_contain])}."
        if not item.allergen_info_complete:
            sentence += " Its allergen information is incomplete."
        if problems:
            sentence += f" I don't recommend it for you: {'; '.join(problems)}."
        sentences.append(sentence)
    return " ".join(sentences)


def comparison(checked: list[tuple[MenuItem, list[str]]]) -> str:
    cheapest = min(checked, key=lambda pair: pair[0].price)[0]
    text = (
        f"Here is {_join([item.name for item, _ in checked])} side by side. "
        f"{cheapest.name} is the least expensive."
    )
    blocked = [f"{item.name} ({'; '.join(problems)})" for item, problems in checked if problems]
    if blocked:
        text += f" Not suitable for you: {_join(blocked)}."
    return text


def unknown_dish(name: str) -> str:
    return f"“{name}” isn't on our menu, so I can't tell you anything about it."
