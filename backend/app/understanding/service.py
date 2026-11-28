"""Combine the language model with deterministic extraction.

The model handles varied phrasing. The rules guarantee that a clearly stated
allergy or price limit is not lost if the model misses it, and take over entirely
if it fails.
"""

import logging
import re

from app import language
from app.memory.policy import normalize
from app.schemas import Candidate, Understanding
from app.understanding import arabic, rules
from app.understanding.llm import LLMError, UnderstandingProvider

logger = logging.getLogger(__name__)

# What a message has to mention before a diet can be set aside for the conversation.
# Arabic is written in its folded spelling.
MEAT_TOPICS = (
    r"vegetarian|veggie|vegan|pescatarian|\b(?:meat|chicken|lamb|beef|fish|prawns?)\b"
    r"|نباتي|لحم|دجاج|سمك|روبيان"
)
DIET_TOPICS = {
    "gluten_free": r"gluten|جلوتين|غلوتين",
    "dairy_free": r"dairy|lactose|milk|cheese|البان|حليب|جبن",
}


def understand(message: str, provider: UnderstandingProvider | None) -> tuple[Understanding, str]:
    """Return the understanding and which engine produced it.

    Engine is "rules" (no model configured), "fallback" (model failed) or the
    provider name.
    """
    baseline = rules.understand(message)
    if provider is None:
        return baseline, "rules"
    try:
        result = provider.understand(message)
    except LLMError as error:
        logger.warning("Language model unavailable, using rules: %s", error)
        return baseline, "fallback"
    return _reconcile(message, result, baseline), provider.name


def _squash(text: str) -> str:
    """Comparable form of a message or a quote from it, in either language."""
    return " ".join(language.fold(text).split())


def _keys(candidate: Candidate) -> set[tuple[str, str]]:
    return {(c.category, c.value) for c in normalize(candidate)}


def _reconcile(message: str, model: Understanding, baseline: Understanding) -> Understanding:
    source = _squash(message)
    # A preference the model cannot quote from the message is treated as invented.
    # Favourite dishes are only ever saved from the menu, never from model output.
    preferences = [
        c for c in model.preferences
        if c.category != "favorite_dish" and c.evidence and _squash(c.evidence) in source
    ]

    # Statements about other people never become the customer's memory. Their allergies
    # still apply to this conversation.
    others = [c for c in preferences if rules.clause_is_about_someone_else(message, c.evidence)]
    preferences = [c for c in preferences if c not in others]
    table = [
        c.value for c in others if c.category == "allergy" and c.operation == "assert"
    ]

    # The model tends to read "I don't eat much meat" as a firm dislike.
    for candidate in preferences:
        wording = _squash(candidate.evidence)
        hedging = (
            rules.HEDGE.search(wording) or rules.SOFTENED.search(wording)
            or arabic.HEDGE.search(wording)
        )
        if candidate.category != "allergy" and hedging:
            candidate.certainty = "uncertain"

    hedged = {key for c in baseline.preferences if c.certainty == "uncertain" for key in _keys(c)}
    for candidate in preferences:
        if candidate.category == "diet" and _keys(candidate) & hedged:
            candidate.certainty = "uncertain"

    seen = {key for c in preferences if c.operation == "assert" for key in _keys(c)}
    preferences += [
        c for c in baseline.preferences
        if c.category == "allergy" and c.operation == "assert" and not _keys(c) <= seen
    ]
    # The model often loses negated spice wording ("I can't handle very spicy food").
    if not any(c.category == "spice" and c.operation == "assert" for c in preferences):
        stated = [c for c in baseline.preferences if c.category == "spice"]
        if stated:
            preferences = [c for c in preferences if c.category != "spice"] + stated
    # A price limit is a hard constraint, so one the model overlooked is restored.
    request = model.request.model_copy(update={
        "allergies": [*model.request.allergies, *baseline.request.allergies, *table]
    })
    if request.max_price is None and not any(c.category == "budget" for c in preferences):
        request = request.model_copy(update={"max_price": baseline.request.max_price})
    # A saved diet is only lifted when the message actually speaks about it.
    request = request.model_copy(update={
        "relaxed_diets": [d for d in request.relaxed_diets if _speaks_of(source, d)]
    })
    return model.model_copy(update={"preferences": preferences, "request": request})


def _speaks_of(message: str, diet: str) -> bool:
    words = DIET_TOPICS.get(diet.lower().replace("-", "_").replace(" ", "_"), MEAT_TOPICS)
    return bool(re.search(words, message))
