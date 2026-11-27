"""Resolve dish names in a message against the menu."""

import re

from app.schemas import MenuItem

GENERIC_WORDS = {
    "classic", "grilled", "plate", "bowl", "chef's", "market", "house", "saffron", "wild",
    "mixed", "sticky", "lemon", "mint", "milk", "grain", "mango", "date", "cheese", "coconut",
    # Ingredient and course words: "something with halloumi" is not a named dish.
    "pistachio", "halloumi", "mushroom", "chickpea", "lentil", "prawns", "falafel", "chicken",
    "paneer", "lamb", "butter", "curry", "soup", "grill", "cream",
}
# Asking "can I have a recommendation?" is not asking for a dish.
NOT_DISH_NAMES = {
    "anything", "something", "recommendation", "suggestion", "option", "options", "food",
    "menu", "more", "one", "meal", "dish", "dishes", "it", "that", "this",
}


def _words(text: str) -> str:
    return " " + " ".join(re.findall(r"[a-z']+", text.lower())) + " "


def _aliases(items: list[MenuItem]) -> dict[str, list[str]]:
    """Full names, ids, and any distinctive word that belongs to only one dish."""
    owners: dict[str, set[str]] = {}
    for item in items:
        for word in _words(item.name).split():
            owners.setdefault(word, set()).add(item.id)
    aliases = {}
    for item in items:
        names = [_words(item.name).strip(), item.id.replace("-", " ")]
        names += [
            word for word in _words(item.name).split()
            if len(owners[word]) == 1 and word not in GENERIC_WORDS and len(word) > 3
        ]
        aliases[item.id] = names
    return aliases


def mentioned(message: str, items: list[MenuItem]) -> list[MenuItem]:
    """Menu items referred to in the message, in the order they appear."""
    text = _words(message)
    found = []
    for item_id, names in _aliases(items).items():
        positions = [text.find(f" {name} ") for name in names if f" {name} " in text]
        if positions:
            found.append((min(positions), item_id))
    by_id = {item.id: item for item in items}
    return [by_id[item_id] for _, item_id in sorted(found)]
