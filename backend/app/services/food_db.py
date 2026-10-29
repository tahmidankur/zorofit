import csv
import os
import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE foods (
    fdc_id INTEGER PRIMARY KEY,
    description TEXT NOT NULL,
    data_type TEXT NOT NULL,
    category TEXT NOT NULL,
    kcal_100g REAL NOT NULL,
    protein_100g REAL NOT NULL,
    carbs_100g REAL NOT NULL,
    fat_100g REAL NOT NULL
);
CREATE TABLE portions (
    id INTEGER PRIMARY KEY,
    fdc_id INTEGER NOT NULL,
    amount REAL NOT NULL,
    unit_name TEXT NOT NULL,
    modifier TEXT NOT NULL,
    gram_weight REAL NOT NULL
);
CREATE INDEX portions_fdc_id ON portions (fdc_id);
CREATE TABLE aliases (
    phrase TEXT PRIMARY KEY,
    fdc_id INTEGER NOT NULL,
    default_unit TEXT NOT NULL
);
CREATE VIRTUAL TABLE foods_fts USING fts5(
    description, content='foods', content_rowid='fdc_id', tokenize='porter unicode61'
);
"""


def _read(path: Path):
    with path.open(newline="", encoding="utf-8") as handle:
        yield from csv.DictReader(handle)


def build_food_db(csv_dir: Path, db_path: Path) -> None:
    # Build into a temp file and rename, so a crash never leaves a half-built foods.db behind.
    tmp_path = db_path.with_suffix(".db.tmp")
    tmp_path.unlink(missing_ok=True)
    conn = sqlite3.connect(tmp_path)
    try:
        conn.executescript(SCHEMA)
        conn.executemany(
            "INSERT INTO foods VALUES (:fdc_id, :description, :data_type, :category,"
            " :kcal_100g, :protein_100g, :carbs_100g, :fat_100g)",
            _read(csv_dir / "foods.csv"),
        )
        conn.executemany(
            "INSERT INTO portions (fdc_id, amount, unit_name, modifier, gram_weight)"
            " VALUES (:fdc_id, :amount, :unit_name, :modifier, :gram_weight)",
            _read(csv_dir / "portions.csv"),
        )
        aliases_path = csv_dir / "aliases.csv"
        if aliases_path.exists():
            conn.executemany(
                "INSERT INTO aliases VALUES (lower(trim(:phrase)), :fdc_id, :default_unit)",
                _read(aliases_path),
            )
        conn.execute("INSERT INTO foods_fts (foods_fts) VALUES ('rebuild')")
        conn.commit()
    finally:
        conn.close()
    os.replace(tmp_path, db_path)


SOURCE_FILES = ("foods.csv", "portions.csv", "aliases.csv")


def ensure_food_db(csv_dir: Path, db_path: Path) -> None:
    # Rebuild when a committed CSV is newer, so alias fixes reach a dev machine without manual steps.
    sources = [csv_dir / name for name in SOURCE_FILES if (csv_dir / name).exists()]
    if not db_path.exists() or any(source.stat().st_mtime > db_path.stat().st_mtime for source in sources):
        build_food_db(csv_dir, db_path)


def connect_read_only(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"{db_path.resolve().as_uri()}?mode=ro", uri=True, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn
