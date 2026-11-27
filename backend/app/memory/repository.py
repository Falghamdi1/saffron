"""SQL for preference records and their history. Callers supply a user session."""

from psycopg import Connection

from app.memory.policy import Change
from app.schemas import Preference

COLUMNS = (
    "id::text, category, value, status, certainty, removal_requested, source_text, "
    "created_at::text, updated_at::text"
)


def lock_user(connection: Connection, user_id: str) -> None:
    """Serialise memory writes for one user until the transaction ends."""
    connection.execute("select pg_advisory_xact_lock(hashtextextended(%s, 0))", (user_id,))


def live_preferences(connection: Connection, user_id: str) -> list[Preference]:
    rows = connection.execute(
        f"select {COLUMNS} from app.preferences "
        "where user_id = %s and status in ('active', 'pending') order by created_at, value",
        (user_id,),
    ).fetchall()
    return [Preference(**row) for row in rows]


def find(connection: Connection, user_id: str, preference_id: str) -> Preference | None:
    row = connection.execute(
        f"select {COLUMNS} from app.preferences where user_id = %s and id = %s",
        (user_id, preference_id),
    ).fetchone()
    return Preference(**row) if row else None


def history(connection: Connection, user_id: str, limit: int = 100) -> list[dict]:
    return connection.execute(
        "select id, preference_id::text, event_type, category, value, reason, source_text, "
        "created_at::text from app.memory_events where user_id = %s order by id desc limit %s",
        (user_id, limit),
    ).fetchall()


def apply_change(connection: Connection, user_id: str, change: Change, source_text: str) -> str:
    """Write one change and its history event. Returns the preference id."""
    preference_id = change.preference_id
    if change.action == "create":
        preference_id = connection.execute(
            "insert into app.preferences "
            "(user_id, category, value, status, certainty, source_text) "
            "values (%s, %s, %s, %s, %s, %s) returning id::text",
            (user_id, change.category, change.value, change.status, change.certainty,
             source_text),
        ).fetchone()["id"]
    else:
        removal = {"flag_removal": True, "clear_removal": False}.get(change.action)
        connection.execute(
            "update app.preferences set status = coalesce(%s, status), "
            "certainty = coalesce(%s, certainty), "
            "removal_requested = coalesce(%s, removal_requested and %s::text is null), "
            "updated_at = now() where user_id = %s and id = %s",
            (change.status, change.certainty, removal, change.status, user_id, preference_id),
        )
    connection.execute(
        "insert into app.memory_events "
        "(user_id, preference_id, event_type, category, value, reason, source_text) "
        "values (%s, %s, %s, %s, %s, %s, %s)",
        (user_id, preference_id, change.event, change.category, change.value, change.reason,
         source_text),
    )
    return preference_id
