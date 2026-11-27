"""Create the schema and load the menu.

    python -m app.setup_db            # against DATABASE_URL

Running it again is safe and updates menu items from data/menu.json.
"""

import json
import sys

import psycopg

from app.config import BACKEND_DIR, ROOT_DIR, Settings
from app.schemas import MenuItem

MIGRATIONS = ROOT_DIR / "supabase" / "migrations"
LOCAL_SHIM = ROOT_DIR / "supabase" / "local_auth_shim.sql"
MENU_FILE = BACKEND_DIR / "data" / "menu.json"


def load_menu_file() -> list[MenuItem]:
    return [MenuItem(**item) for item in json.loads(MENU_FILE.read_text(encoding="utf-8"))]


def setup_database(url: str, *, local: bool = False) -> None:
    columns = list(MenuItem.model_fields)
    upsert = (
        f"insert into app.menu_items ({', '.join(columns)}) "
        f"values ({', '.join(f'%({c})s' for c in columns)}) "
        f"on conflict (id) do update set "
        f"{', '.join(f'{c} = excluded.{c}' for c in columns if c != 'id')}"
    )
    with psycopg.connect(url, prepare_threshold=None) as connection:
        if local:
            connection.execute(LOCAL_SHIM.read_text(encoding="utf-8"))
        for migration in sorted(MIGRATIONS.glob("*.sql")):
            connection.execute(migration.read_text(encoding="utf-8"))
        items = load_menu_file()
        with connection.cursor() as cursor:
            cursor.executemany(upsert, [item.model_dump() for item in items])


def main() -> None:
    settings = Settings()
    if not settings.database_url:
        sys.exit("DATABASE_URL is not set. Local mode creates its database automatically.")
    setup_database(settings.database_url, local=settings.auth_mode == "local")
    print(f"Schema applied and {len(load_menu_file())} menu items loaded.")


if __name__ == "__main__":
    main()
