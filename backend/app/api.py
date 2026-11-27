"""HTTP routes. Each user route derives identity from the verified access token."""

import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, field_validator

from app.auth import User, current_user, issue_local_token
from app.chat import repository as chat_repository
from app.chat.service import ConversationNotFound, handle_message
from app.db import Database
from app.memory import repository as memory_repository
from app.memory import service as memory_service
from app.menu import load_menu
from app.recommendation.engine import build_profile, violations
from app.schemas import Candidate, RequestConstraints
from app.vocabulary import ALLERGENS

router = APIRouter(prefix="/api")


class ChatRequest(BaseModel):
    message: str = Field(max_length=1000)
    conversation_id: uuid.UUID | None = None

    @field_validator("message")
    @classmethod
    def not_blank(cls, value: str) -> str:
        value = value.replace("\x00", "").strip()
        if not value:
            raise ValueError("Message is empty")
        return value


class LocalSignIn(BaseModel):
    name: str = Field(min_length=1, max_length=40, pattern=r"^[\w .@-]+$")


class AllergyEntry(BaseModel):
    allergen: Literal[ALLERGENS]


def database(request: Request) -> Database:
    return request.app.state.database


def signed_in(user: User = Depends(current_user), db: Database = Depends(database)) -> User:
    """A verified user with a profile row (created on first request)."""
    with db.user_session(user.id) as connection:
        name = (user.email.split("@")[0] or "Guest")[:80]
        connection.execute(
            "insert into app.profiles (id, display_name) values (%s, %s) "
            "on conflict (id) do nothing",
            (user.id, name),
        )
    return user


@router.get("/health")
def health(db: Database = Depends(database)) -> dict:
    with db.admin_session() as connection:
        count = connection.execute("select count(*) as n from app.menu_items").fetchone()["n"]
    return {"status": "ok", "menu_items": count}


@router.get("/config")
def config(request: Request) -> dict:
    settings = request.app.state.settings
    return {
        "auth_mode": settings.auth_mode,
        "supabase_url": settings.supabase_url,
        # Publishable by design: it grants nothing without a signed-in user.
        "supabase_anon_key": settings.supabase_anon_key,
        "language_model": request.app.state.provider is not None,
    }


@router.post("/local-auth/session")
def local_sign_in(body: LocalSignIn, request: Request, db: Database = Depends(database)) -> dict:
    settings = request.app.state.settings
    if settings.auth_mode != "local":
        raise HTTPException(404, "Not found")
    name = body.name.strip().lower()
    user_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"saffron-local:{name}"))
    with db.admin_session() as connection:
        connection.execute(
            "insert into auth.users (id) values (%s) on conflict do nothing", (user_id,)
        )
    return {"access_token": issue_local_token(settings, user_id, name)}


@router.post("/chat")
def chat(
    body: ChatRequest, request: Request,
    user: User = Depends(signed_in), db: Database = Depends(database),
) -> dict:
    if not request.app.state.rate_limiter.allow(user.id):
        raise HTTPException(429, "You're sending messages very quickly. Please wait a minute.")
    conversation_id = str(body.conversation_id) if body.conversation_id else None
    try:
        return handle_message(
            db, request.app.state.provider, user.id, body.message, conversation_id
        )
    except ConversationNotFound as error:
        raise HTTPException(404, "Conversation not found") from error


@router.get("/conversations")
def conversations(user: User = Depends(signed_in), db: Database = Depends(database)) -> list[dict]:
    with db.user_session(user.id) as connection:
        return chat_repository.recent(connection, user.id)


@router.get("/conversations/{conversation_id}/messages")
def conversation_messages(
    conversation_id: uuid.UUID,
    user: User = Depends(signed_in), db: Database = Depends(database),
) -> list[dict]:
    with db.user_session(user.id) as connection:
        if chat_repository.get(connection, user.id, str(conversation_id)) is None:
            raise HTTPException(404, "Conversation not found")
        return chat_repository.messages(connection, user.id, str(conversation_id))


@router.get("/menu")
def menu(user: User = Depends(signed_in), db: Database = Depends(database)) -> list[dict]:
    """The full menu, each dish marked with why it does not suit this user."""
    with db.user_session(user.id) as connection:
        memory = memory_repository.live_preferences(connection, user.id)
        items = load_menu(connection)
    # Budget is per request, so browsing does not flag prices.
    profile = build_profile(
        [p for p in memory if p.category != "budget"], RequestConstraints()
    )
    return [{**i.model_dump(), "violations": violations(i, profile)} for i in items]


@router.post("/favorites/{item_id}")
def add_favorite(
    item_id: str, user: User = Depends(signed_in), db: Database = Depends(database)
) -> dict:
    with db.user_session(user.id) as connection:
        item = next((i for i in load_menu(connection) if i.id == item_id), None)
        if item is None:
            raise HTTPException(404, "That dish is not on the menu")
        notes = memory_service.remember(
            connection, user.id,
            [Candidate(category="favorite_dish", value=item.id)],
            f"Saved {item.name} as a favourite",
        )
    return {"memory_notes": [n.model_dump() for n in notes]}


def _memory_view(db: Database, user_id: str) -> dict:
    with db.user_session(user_id) as connection:
        return {
            "preferences": [
                p.model_dump() for p in memory_repository.live_preferences(connection, user_id)
            ],
            "history": memory_repository.history(connection, user_id),
        }


@router.get("/memory")
def memory(user: User = Depends(signed_in), db: Database = Depends(database)) -> dict:
    return _memory_view(db, user.id)


@router.post("/memory/allergies")
def add_allergy(
    body: AllergyEntry,
    user: User = Depends(signed_in), db: Database = Depends(database),
) -> dict:
    """Record an allergy directly, without relying on message understanding."""
    with db.user_session(user.id) as connection:
        memory_service.remember(
            connection, user.id,
            [Candidate(category="allergy", value=body.allergen)],
            "Added in the preferences panel",
        )
    return _memory_view(db, user.id)


def _change_preference(db: Database, user_id: str, preference_id: uuid.UUID, action) -> dict:
    with db.user_session(user_id) as connection:
        memory_repository.lock_user(connection, user_id)
        preference = memory_repository.find(connection, user_id, str(preference_id))
        if preference is None or preference.status not in ("active", "pending"):
            raise HTTPException(404, "Preference not found")
        action(connection, user_id, preference)
    return _memory_view(db, user_id)


@router.post("/memory/{preference_id}/confirm")
def confirm_preference(
    preference_id: uuid.UUID,
    user: User = Depends(signed_in), db: Database = Depends(database),
) -> dict:
    return _change_preference(db, user.id, preference_id, memory_service.confirm)


@router.post("/memory/{preference_id}/dismiss")
def dismiss_preference(
    preference_id: uuid.UUID,
    user: User = Depends(signed_in), db: Database = Depends(database),
) -> dict:
    return _change_preference(db, user.id, preference_id, memory_service.dismiss)


@router.delete("/memory/{preference_id}")
def forget_preference(
    preference_id: uuid.UUID,
    user: User = Depends(signed_in), db: Database = Depends(database),
) -> dict:
    return _change_preference(db, user.id, preference_id, memory_service.forget)
