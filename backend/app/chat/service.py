"""One chat turn: understand, update memory, recommend, reply."""

from dataclasses import dataclass, field, replace

from psycopg import Connection
from psycopg.types.json import Jsonb

from app.chat import context, reply, repository
from app.db import Database
from app.memory import repository as memory_repository
from app.memory import service as memory_service
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

    with database.user_session(user_id) as connection:
        if conversation_id is None:
            conversation = repository.create(connection, user_id, message)
        else:
            conversation = repository.get(connection, user_id, conversation_id)
            if conversation is None:
                raise ConversationNotFound
        conversation_id = conversation["id"]
        repository.add_message(connection, user_id, conversation_id, "user", message)

        notes = memory_service.remember(
            connection, user_id, understanding.preferences, message
        )
        state = conversation["context"]
        request = context.merge(
            RequestConstraints(**state.get("request", {})),
            context.clean(understanding.request),
            understanding.preferences,
        )
        turn, profile = _respond(
            connection, user_id, message, understanding, request, state.get("shown", []), notes
        )

        payload = {
            "recommendations": [r.model_dump() for r in turn.recommendations],
            "comparison": turn.comparison,
            "memory_notes": [n.model_dump() for n in notes],
            "notice": reply.safety_notice(profile)
            if turn.recommendations or turn.comparison else "",
            "engine": engine,
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


def _respond(
    connection: Connection,
    user_id: str,
    message: str,
    understanding: Understanding,
    request: RequestConstraints,
    shown: list[str],
    notes: list[MemoryNote],
) -> tuple[Turn, Profile]:
    memory: list[Preference] = memory_repository.live_preferences(connection, user_id)
    menu = load_menu(connection)
    profile = build_profile(memory, request)
    mentioned = dishes.mentioned(message, menu)
    intent = understanding.intent
    prefix = reply.acknowledgement(notes)

    def respond(turn: Turn) -> tuple[Turn, Profile]:
        turn.text = f"{prefix} {turn.text}".strip()
        return turn, profile

    def checked(items: list[MenuItem]) -> list[tuple[MenuItem, list[str]]]:
        # A question about a named dish is not limited to the current course filter.
        return [(item, violations(item, profile)) for item in items]

    def table(pairs: list[tuple[MenuItem, list[str]]]) -> list[dict]:
        return [{"item": i.model_dump(), "violations": v} for i, v in pairs]

    if intent == "compare":
        by_id = {item.id: item for item in menu}
        targets = mentioned if len(mentioned) >= 2 else [by_id[i] for i in shown if i in by_id]
        if len(targets) < 2:
            return respond(Turn("Which two dishes would you like me to compare?"))
        pairs = checked(targets[:3])
        return respond(Turn(
            reply.comparison(pairs), comparison=table(pairs), shown=[i.id for i, _ in pairs]
        ))

    if mentioned and intent != "share" and not understanding.request.cheaper:
        pairs = checked(mentioned[:3])
        return respond(Turn(
            reply.dish_facts(pairs), comparison=table(pairs), shown=[i.id for i, _ in pairs]
        ))

    unknown = ""
    missing = _unknown_dishes(understanding, menu) if intent == "dish_question" else []
    if missing:
        unknown = reply.unknown_dish(missing[0][:60]) + " These are on the menu instead."
        # Do not keep searching for something the kitchen does not make.
        request.wants = [w for w in request.wants if singular(w) not in map(singular, missing)]
        profile = build_profile(memory, request)

    refresh_after_change = intent == "share" and shown and notes
    if not (intent in ("recommend", "dish_question") or refresh_after_change):
        if intent == "greeting":
            return respond(Turn(f"Welcome to Saffron. {reply.HELP}"))
        if intent == "share" and notes:
            return respond(Turn("Would you like some suggestions?"))
        return respond(Turn("" if prefix else reply.HELP))

    cheaper = understanding.request.cheaper
    if cheaper:
        previous = [item for item in menu if item.id in shown]
        if previous:
            cap = min(item.price for item in previous) - 0.01
            # "Cheaper" means a cheaper alternative to the same course.
            profile = replace(
                profile,
                category=profile.category or previous[0].category,
                max_price=min(cap, profile.max_price or cap),
            )

    result = recommend(menu, profile)
    names = [r.item.name for r in result.recommendations]
    text = reply.recommendations(names, result.excluded, result.unmatched_wants, cheaper)
    return respond(Turn(
        f"{unknown} {text}".strip(),
        recommendations=result.recommendations,
        shown=[r.item.id for r in result.recommendations],
    ))


def _unknown_dishes(understanding: Understanding, menu: list[MenuItem]) -> list[str]:
    """Dish names the user asked for that match nothing the kitchen makes."""
    names = [
        name for name in understanding.dish_names
        if not set(name.lower().split()) & dishes.NOT_DISH_NAMES
        and not any(matches_food(item, name) for item in menu)
    ]
    # "Do you have vegan desserts?" is a filtered request, not a missing dish. A model
    # may also list the unknown dish as a wanted food, which does not count.
    asked = {singular(name) for name in names}
    other = understanding.request.model_copy(update={
        "wants": [w for w in understanding.request.wants if singular(w) not in asked]
    })
    return names if other == RequestConstraints() else []
