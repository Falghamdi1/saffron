"""Menu records are the only source of dish facts."""

from psycopg import Connection

from app.schemas import MenuItem


def load_menu(connection: Connection) -> list[MenuItem]:
    rows = connection.execute(
        "select * from app.menu_items order by "
        "array_position(array['starter', 'main', 'dessert', 'drink'], category), price, name"
    ).fetchall()
    return [MenuItem(**row) for row in rows]
