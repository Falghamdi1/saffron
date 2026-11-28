"""Compose the assistant's text.

Every dish name, price and allergen fact here is copied from menu records chosen by
the recommender. No language model writes this text, so it cannot invent a dish.
"""

from app.i18n import join, name, say
from app.recommendation.engine import Profile
from app.schemas import Exclusion, MemoryNote, MenuItem
from app.vocabulary import ALLERGENS


def dish_name(item: MenuItem, lang: str) -> str:
    return item.name_ar if lang == "ar" and item.name_ar else item.name


def safety_notice(profile: Profile) -> str:
    lang = profile.language
    allergies = sorted(profile.allergies | profile.unconfirmed_allergies)
    if not allergies:
        return ""
    notice = say(lang, "notice", allergies=join([name(a, lang) for a in allergies], lang))
    untracked = [name(a, lang) for a in allergies if a not in ALLERGENS]
    if untracked:
        names = join(untracked, lang)
        names = names.capitalize() if lang == "en" else names
        notice += " " + say(lang, "untracked", names=names)
    return notice


def table_allergies(allergies: list[str], lang: str) -> str:
    return say(lang, "table", allergies=join([name(a, lang) for a in allergies], lang))


def acknowledgement(notes: list[MemoryNote]) -> str:
    return " ".join(note.message for note in notes)


def recommendations(
    items: list[MenuItem],
    excluded: list[Exclusion],
    unmatched: list[str],
    cheaper: bool,
    lang: str,
) -> str:
    parts = []
    if unmatched:
        wants = join([name(w, lang) for w in unmatched], lang)
        parts.append(say(lang, "unmatched", wants=wants))
    if not items:
        parts.append(say(lang, "nothing_cheaper" if cheaper else "nothing"))
        return " ".join(parts)
    names = join([dish_name(i, lang) for i in items], lang)
    parts.append(say(lang, "here_one" if len(items) == 1 else "here_many", names=names))
    if excluded:
        count = len(excluded)
        key = "left_out_one" if count == 1 else "left_out_many"
        parts.append(say(lang, key, count=count))
    return " ".join(parts)


def earlier_limit(amount: float, lang: str) -> str:
    return say(lang, "earlier_limit", amount=f"{amount:g}")


def dish_facts(checked: list[tuple[MenuItem, list[str]]], lang: str) -> str:
    separator = "، " if lang == "ar" else ", "
    sentences = []
    for item, problems in checked:
        ingredients = item.ingredients_ar if lang == "ar" else item.ingredients
        listed = (
            join([name(a, lang) for a in item.allergens], lang)
            if item.allergens else say(lang, "none_recorded")
        )
        sentence = say(
            lang, "facts", name=dish_name(item, lang), price=f"{item.price:g}",
            ingredients=separator.join(ingredients), allergens=listed,
        )
        if item.may_contain:
            may = join([name(a, lang) for a in item.may_contain], lang)
            sentence += " " + say(lang, "may_contain", allergens=may)
        if not item.allergen_info_complete:
            sentence += " " + say(lang, "incomplete")
        if problems:
            sentence += " " + say(lang, "not_for_you", problems="; ".join(problems))
        sentences.append(sentence)
    return " ".join(sentences)


def comparison(checked: list[tuple[MenuItem, list[str]]], lang: str) -> str:
    cheapest = min(checked, key=lambda pair: pair[0].price)[0]
    text = say(
        lang, "compare",
        names=join([dish_name(item, lang) for item, _ in checked], lang),
        cheapest=dish_name(cheapest, lang),
    )
    blocked = [
        f"{dish_name(item, lang)} ({'; '.join(problems)})"
        for item, problems in checked if problems
    ]
    if blocked:
        text += " " + say(lang, "unsuitable", dishes=join(blocked, lang))
    return text
