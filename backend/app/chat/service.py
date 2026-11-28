"""One chat turn: understand, update memory, recommend, reply."""

import logging
from dataclasses import dataclass, field, replace

from psycopg import Connection
from psycopg.types.json import Jsonb

from app.chat import context, reply, repository
from app.db import Database
from app.i18n import language_of, say
from app.memory import repository as memory_repository
from app.memory import service as memory_service
from app.memory.policy import unidentified
from app.menu import load_menu
from app.recommendation import dishes
from app.recommendation.engine import Profile, build_profile, matches_food, recommend, violations
from app.schemas import (
    MemoryNote,
    MenuItem,
    Preference,
    Recommendation,
    RequestConstraints,
    Understanding,
)
from app.understanding.llm import UnderstandingProvider
from app.understanding.service import understand
from app.vocabulary import singular

logger = logging.getLogger(__name__)


class ConversationNotFound(Exception):
    pass


@dataclass
class Turn:
    text: str
    recommendations: list[Recommendation] = field(default_factory=list)
    comparison: list[dict] = field(default_factory=list)
    shown: list[str] = field(default_factory=list)


def handle_message(
    database: Database,
    provider: UnderstandingProvider | None,
    user_id: str,
    message: str,
    conversation_id: str | None,
) -> dict:
    # The model call happens before the transaction so no connection waits on it.
    understanding, engine = understand(message, provider)
    # Counting engines shows how often the fallback is used. No message text is logged.
    logger.info("turn understood by %s", engine)

    with database.user_session(user_id) as connection:
        if conversation_id is None:
            conversation = repository.create(connection, user_id, message)
        else:
            conversation = repository.get(connection, user_id, conversation_id)
            if conversation is None:
                raise ConversationNotFound
        conversation_id = conversation["id"]
        repository.add_message(connection, user_id, conversation_id, "user", message)

        lang = language_of(message)
        notes = memory_service.remember(
            connection, user_id, understanding.preferences, message, lang
        )
        state = conversation["context"]
        previous = RequestConstraints(**state.get("request", {}))
        stated = context.clean(understanding.request)
        request = context.merge(previous, stated, understanding.preferences)
        _note_table_allergies(connection, user_id, previous, request, notes, lang)
        # A price limit carried from an earlier message is worth mentioning when it bites.
        earlier_limit = None
        if stated.max_price is None and request.max_price == previous.max_price:
            earlier_limit = previous.max_price
        turn, profile = _respond(
            connection, user_id, message, understanding, request,
            state.get("shown", []), notes, earlier_limit,
        )

        payload = {
            "recommendations": [r.model_dump() for r in turn.recommendations],
            "comparison": turn.comparison,
            "memory_notes": [n.model_dump() for n in notes],
            "notice": reply.safety_notice(profile)
            if turn.recommendations or turn.comparison else "",
            "engine": engine,
            "lang": lang,
        }
        repository.add_message(
            connection, user_id, conversation_id, "assistant", turn.text, payload
        )
        repository.save_context(connection, user_id, conversation_id, Jsonb({
            "request": request.model_dump(exclude_defaults=True),
            "shown": turn.shown or state.get("shown", []),
        }))

    return {
        "conversation_id": conversation_id,
        "message": {"role": "assistant", "content": turn.text, "payload": payload},
    }


def _note_table_allergies(
    connection: Connection,
    user_id: str,
    previous: RequestConstraints,
    request: RequestConstraints,
    notes: list[MemoryNote],
    lang: str,
) -> None:
    """Say which allergies now apply to this chat without being the customer's own."""
    known = set(previous.allergies) | {
        p.value for p in memory_repository.live_preferences(connection, user_id)
        if p.category == "allergy"
    }
    added = [a for a in request.allergies if a not in known]
    if added:
        message = reply.table_allergies(added, lang)
        notes.append(MemoryNote(kind="temporary", message=message))


def _respond(
    connection: Connection,
    user_id: str,
    message: str,
    understanding: Understanding,
    request: RequestConstraints,
    shown: list[str],
    notes: list[MemoryNote],
    earlier_limit: float | None,
) -> tuple[Turn, Profile]:
    """Choose the kind of answer this message needs. May drop spent wants from `request`."""
    memory: list[Preference] = memory_repository.live_preferences(connection, user_id)
    menu = load_menu(connection)
    lang = language_of(message)
    profile = build_profile(memory, request, lang)
    mentioned = dishes.mentioned(message, menu)
    intent = understanding.intent
    unknown = ""

    if intent == "compare":
        by_id = {item.id: item for item in menu}
        targets = mentioned if len(mentioned) >= 2 else [by_id[i] for i in shown if i in by_id]
        if len(targets) < 2:
            turn = Turn(say(lang, "which_dishes"))
        else:
            request.wants = []  # a question about named dishes is not a standing request
            turn = _named_dishes(targets[:3], profile, reply.comparison)
    elif mentioned and intent != "share" and not understanding.request.cheaper:
        request.wants = []
        turn = _named_dishes(mentioned[:3], profile, reply.dish_facts)
    else:
        missing = _unknown_dishes(understanding, menu) if intent == "dish_question" else []
        if missing:
            unknown = say(lang, "unknown_dish", name=missing[0][:60])
            unknown += " " + say(lang, "instead")
            # Do not keep searching for something the kitchen does not make.
            request.wants = [w for w in request.wants if singular(w) not in map(singular, missing)]
            profile = build_profile(memory, request, lang)

        refresh_after_change = intent == "share" and shown and notes
        if intent in ("recommend", "dish_question") or refresh_after_change:
            turn = _suggestions(
                menu, profile, shown, understanding.request.cheaper, earlier_limit
            )
        elif intent == "greeting":
            turn = Turn(f"{say(lang, 'welcome')} {say(lang, 'help')}")
        elif intent == "share" and notes:
            turn = Turn(say(lang, "offer"))
        else:
            turn = Turn("" if notes else say(lang, "help"))

    turn.text = " ".join(
        part for part in (reply.acknowledgement(notes), unknown, turn.text) if part
    )
    return turn, profile


def _named_dishes(items: list[MenuItem], profile: Profile, describe) -> Turn:
    """Facts about specific dishes, each checked against the diner's requirements."""
    # A question about a named dish is not limited to the current course filter.
    pairs = [(item, violations(item, profile)) for item in items]
    return Turn(
        describe(pairs, profile.language),
        comparison=[{"item": i.model_dump(), "violations": v} for i, v in pairs],
        shown=[i.id for i, _ in pairs],
    )


def _suggestions(
    menu: list[MenuItem],
    profile: Profile,
    shown: list[str],
    cheaper: bool,
    earlier_limit: float | None,
) -> Turn:
    if cheaper:
        last = [item for item in menu if item.id in shown]
        if last:
            cap = min(item.price for item in last) - 0.01
            # "Cheaper" means a cheaper alternative to the same course.
            profile = replace(
                profile,
                category=profile.category or last[0].category,
                max_price=min(cap, profile.max_price or cap),
            )

    result = recommend(menu, profile)
    if any(unidentified(a) for a in profile.allergies | profile.unconfirmed_allergies):
        return Turn(say(profile.language, "blocked"))
    text = reply.recommendations(
        [r.item for r in result.recommendations],
        result.excluded, result.unmatched_wants, cheaper, profile.language,
    )
    limit = profile.max_price
    over_budget = limit is not None and any(
        item.price > limit for item in menu if item.id in {e.item_id for e in result.excluded}
    )
    if earlier_limit and over_budget and not cheaper:
        text += " " + reply.earlier_limit(earlier_limit, profile.language)
    return Turn(
        text,
        recommendations=result.recommendations,
        shown=[r.item.id for r in result.recommendations],
    )


def _unknown_dishes(understanding: Understanding, menu: list[MenuItem]) -> list[str]:
    """Dish names the user asked for that match nothing the kitchen makes."""
    names = [
        name for name in understanding.dish_names
        if not set(name.lower().split()) & dishes.NOT_DISH_NAMES
        and not any(matches_food(item, name) for item in menu)
        and not dishes.mentioned(name, menu)
    ]
    # "Do you have vegan desserts?" is a filtered request, not a missing dish. A model
    # may also list the unknown dish as a wanted food, which does not count.
    asked = {singular(name) for name in names}
    other = understanding.request.model_copy(update={
        "wants": [w for w in understanding.request.wants if singular(w) not in asked],
        "allergies": [],
    })
    return names if other == RequestConstraints() else []
