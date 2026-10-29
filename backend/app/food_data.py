import sqlite3

from app.config import DATA_DIR, settings
from app.services.food_db import connect_read_only, ensure_food_db


def prepare_food_db() -> None:
    ensure_food_db(DATA_DIR, settings.foods_db_path)


def get_food_db():
    conn: sqlite3.Connection = connect_read_only(settings.foods_db_path)
    try:
        yield conn
    finally:
        conn.close()
