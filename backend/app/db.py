"""Database access.

Every query made for a user goes through `user_session`, which drops to the
`authenticated` role and sets the verified user id for the transaction, so Row
Level Security applies even if a query forgets to filter by user.
"""

import json
from collections.abc import Iterator
from contextlib import contextmanager

from psycopg import Connection
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool


class Database:
    def __init__(self, url: str, max_size: int = 5) -> None:
        # Prepared statements are disabled for Supabase's transaction-mode pooler.
        self._pool = ConnectionPool(
            url,
            min_size=1,
            max_size=max_size,
            kwargs={"row_factory": dict_row, "prepare_threshold": None},
            check=ConnectionPool.check_connection,
            open=True,
        )

    @contextmanager
    def user_session(self, user_id: str) -> Iterator[Connection]:
        claims = json.dumps({"sub": user_id, "role": "authenticated"})
        with self._pool.connection() as connection, connection.transaction():
            connection.execute("select set_config('request.jwt.claims', %s, true)", (claims,))
            connection.execute("set local role authenticated")
            yield connection

    @contextmanager
    def admin_session(self) -> Iterator[Connection]:
        """Privileged access for migrations, seeding and health checks only."""
        with self._pool.connection() as connection, connection.transaction():
            yield connection

    def close(self) -> None:
        self._pool.close()
