"""Combine the language model with deterministic extraction.

The model handles varied phrasing. The rules guarantee that a clearly stated
allergy or price limit is not lost if the model misses it, and take over entirely
if it fails.
"""

import logging

from app.memory.policy import normalize
from app.schemas import Candidate, Understanding
from app.understanding import rules
from app.understanding.llm import LLMError, UnderstandingProvider

logger = logging.getLogger(__name__)


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
    return " ".join(text.lower().replace("’", "'").split())


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

    # The model tends to read "I don't eat much meat" as a firm dislike.
    for candidate in preferences:
        wording = _squash(candidate.evidence)
        hedging = rules.HEDGE.search(wording) or rules.SOFTENED.search(wording)
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
    # A price limit is a hard constraint, so one the model overlooked is restored.
    request = model.request
    if request.max_price is None and not any(c.category == "budget" for c in preferences):
        request = request.model_copy(update={"max_price": baseline.request.max_price})
    return model.model_copy(update={"preferences": preferences, "request": request})
