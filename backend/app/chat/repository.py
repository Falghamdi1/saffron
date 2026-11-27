"""SQL for conversations and messages. Callers supply a user session."""

from psycopg import Connection
from psycopg.types.json import Jsonb


def create(connection: Connection, user_id: str, first_message: str) -> dict:
    title = " ".join(first_message.split())
    if len(title) > 60:
        title = title[:59] + "…"
    return connection.execute(
        "insert into app.conversations (user_id, title) values (%s, %s) "
        "returning id::text, title, context",
        (user_id, title),
    ).fetchone()


def get(connection: Connection, user_id: str, conversation_id: str) -> dict | None:
    return connection.execute(
        "select id::text, title, context from app.conversations "
        "where user_id = %s and id = %s for update",
        (user_id, conversation_id),
    ).fetchone()


def recent(connection: Connection, user_id: str) -> list[dict]:
    return connection.execute(
        "select id::text, title, updated_at::text from app.conversations "
        "where user_id = %s order by updated_at desc limit 30",
        (user_id,),
    ).fetchall()


def messages(connection: Connection, user_id: str, conversation_id: str) -> list[dict]:
    return connection.execute(
        "select role, content, payload from app.messages "
        "where user_id = %s and conversation_id = %s order by id",
        (user_id, conversation_id),
    ).fetchall()


def add_message(
    connection: Connection, user_id: str, conversation_id: str,
    role: str, content: str, payload: dict | None = None,
) -> None:
    connection.execute(
        "insert into app.messages (conversation_id, user_id, role, content, payload) "
        "values (%s, %s, %s, %s, %s)",
        (conversation_id, user_id, role, content[:4000], Jsonb(payload or {})),
    )


def save_context(
    connection: Connection, user_id: str, conversation_id: str, context: Jsonb
) -> None:
    connection.execute(
        "update app.conversations set context = %s, updated_at = now() "
        "where user_id = %s and id = %s",
        (context, user_id, conversation_id),
    )
