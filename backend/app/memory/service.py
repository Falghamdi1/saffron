"""The only write path to long-term memory: normalise, decide, persist."""

from psycopg import Connection

from app.memory import repository
from app.memory.policy import Change, decide, describe, normalize
from app.schemas import Candidate, MemoryNote, Preference


def remember(
    connection: Connection,
    user_id: str,
    candidates: list[Candidate],
    source_text: str,
    lang: str = "en",
) -> list[MemoryNote]:
    repository.lock_user(connection, user_id)
    notes: list[MemoryNote] = []
    # Retractions run first so "I no longer like X, I hate it" resolves cleanly.
    ordered = sorted(candidates, key=lambda c: c.operation != "retract")
    for candidate in ordered:
        for canonical in normalize(candidate):
            decision = decide(canonical, repository.live_preferences(connection, user_id), lang)
            created_id = None
            for change in decision.changes:
                preference_id = repository.apply_change(connection, user_id, change, source_text)
                if change.action == "create":
                    created_id = preference_id
            for note in decision.notes:
                if note.kind == "needs_confirmation" and note.preference_id is None:
                    note.preference_id = created_id
                notes.append(note)
    return list({note.message: note for note in notes}.values())


def confirm(connection: Connection, user_id: str, preference: Preference) -> None:
    """The user approved a pending preference or a requested removal."""
    repository.lock_user(connection, user_id)
    source = "Confirmed in the memory panel"
    if preference.removal_requested:
        _retract(connection, user_id, preference, "retracted", "Removal confirmed by you", source)
    elif preference.status == "pending":
        candidate = Candidate(category=preference.category, value=preference.value)
        decision = decide(candidate, repository.live_preferences(connection, user_id))
        for change in decision.changes:
            repository.apply_change(connection, user_id, change, source)


def dismiss(connection: Connection, user_id: str, preference: Preference) -> None:
    """The user rejected a pending preference or a requested removal."""
    repository.lock_user(connection, user_id)
    source = "Dismissed in the memory panel"
    if preference.status == "pending":
        _retract(connection, user_id, preference, "dismissed", "You said this is not right", source)
    elif preference.removal_requested:
        repository.apply_change(connection, user_id, Change(
            "clear_removal", "reaffirmed", "You chose to keep it",
            preference.category, preference.value, preference.id,
        ), source)


def forget(connection: Connection, user_id: str, preference: Preference) -> None:
    """Explicit removal from the memory panel, including allergies."""
    repository.lock_user(connection, user_id)
    _retract(
        connection, user_id, preference, "retracted",
        f"You removed {describe(preference.category, preference.value)}",
        "Removed in the memory panel",
    )


def _retract(
    connection: Connection, user_id: str, preference: Preference,
    event: str, reason: str, source: str,
) -> None:
    repository.apply_change(connection, user_id, Change(
        "update", event, reason, preference.category, preference.value, preference.id,
        status="retracted",
    ), source)
