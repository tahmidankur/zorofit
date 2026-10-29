import difflib
import re
import sqlite3
from dataclasses import dataclass, field

from app.services.portions import PortionRow, singular


@dataclass
class FoodMatch:
    fdc_id: int
    description: str
    category: str
    kcal_100g: float
    protein_100g: float
    carbs_100g: float
    fat_100g: float
    default_unit: str = ""
    portions: list[PortionRow] = field(default_factory=list)
    # True when only some of the query words matched, so the food is a guess, not a match.
    partial: bool = False


def normalize_phrase(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def _match_from_row(row: sqlite3.Row, default_unit: str = "") -> FoodMatch:
    return FoodMatch(
        fdc_id=row["fdc_id"],
        description=row["description"],
        category=row["category"],
        kcal_100g=row["kcal_100g"],
        protein_100g=row["protein_100g"],
        carbs_100g=row["carbs_100g"],
        fat_100g=row["fat_100g"],
        default_unit=default_unit,
    )


def get_food(conn: sqlite3.Connection, fdc_id: int) -> FoodMatch | None:
    row = conn.execute("SELECT * FROM foods WHERE fdc_id = ?", (fdc_id,)).fetchone()
    if row is None:
        return None
    match = _match_from_row(row)
    match.portions = get_portions(conn, fdc_id)
    return match


def get_portions(conn: sqlite3.Connection, fdc_id: int) -> list[PortionRow]:
    rows = conn.execute(
        "SELECT amount, unit_name, modifier, gram_weight FROM portions WHERE fdc_id = ? ORDER BY id",
        (fdc_id,),
    )
    return [PortionRow(row["amount"], row["unit_name"], row["modifier"], row["gram_weight"]) for row in rows]


def alias_lookup(conn: sqlite3.Connection, text: str) -> FoodMatch | None:
    phrase = normalize_phrase(text)
    candidates = [phrase, " ".join(singular(word) for word in phrase.split(" "))]
    for candidate in candidates:
        row = conn.execute(
            "SELECT f.*, a.default_unit FROM aliases a JOIN foods f ON f.fdc_id = a.fdc_id WHERE a.phrase = ?",
            (candidate,),
        ).fetchone()
        if row:
            return _match_from_row(row, row["default_unit"])
    return None


def _head_rank(description: str, tokens: list[str]) -> int:
    head = description.lower().split(",")[0]
    head_words = [singular(word) for word in re.findall(r"[a-z0-9]+", head)]
    query = [singular(token) for token in tokens]
    if head_words == query:
        return 0
    if head_words[:1] == query[:1]:
        return 1
    return 2


def _fts(conn: sqlite3.Connection, tokens: list[str], joiner: str, limit: int) -> list[FoodMatch]:
    query = f" {joiner} ".join(f'"{token}"*' for token in tokens)
    rows = conn.execute(
        """
        SELECT f.* FROM foods_fts
        JOIN foods f ON f.fdc_id = foods_fts.rowid
        WHERE foods_fts MATCH ?
        ORDER BY bm25(foods_fts)
        LIMIT 80
        """,
        (query,),
    ).fetchall()
    # bm25 alone puts "Eggnog" above "Egg, whole"; a food named after the query word should win.
    ranked = sorted(
        enumerate(rows),
        key=lambda pair: (_head_rank(pair[1]["description"], tokens), pair[0], len(pair[1]["description"])),
    )
    matches, seen = [], set()
    for _, row in ranked:
        if row["description"] in seen:
            continue
        seen.add(row["description"])
        matches.append(_match_from_row(row))
        if len(matches) == limit:
            break
    return matches


_vocabularies: dict[str, list[str]] = {}


def _vocabulary(conn: sqlite3.Connection) -> list[str]:
    db_file = conn.execute("PRAGMA database_list").fetchone()["file"]
    if db_file not in _vocabularies:
        words = set()
        for (description,) in conn.execute("SELECT description FROM foods"):
            words.update(word for word in _tokens(description) if len(word) > 2 and not word.isdigit())
        _vocabularies[db_file] = sorted(words)
    return _vocabularies[db_file]


def _spell_corrected(conn: sqlite3.Connection, tokens: list[str]) -> list[str]:
    vocabulary = _vocabulary(conn)
    corrected = []
    for token in tokens:
        close = difflib.get_close_matches(token, vocabulary, n=1, cutoff=0.8)
        corrected.append(close[0] if close else token)
    return corrected


def search(conn: sqlite3.Connection, text: str, limit: int = 8) -> list[FoodMatch]:
    tokens = _tokens(text)
    if not tokens:
        return []
    results: list[FoodMatch] = []
    alias = alias_lookup(conn, text)
    if alias:
        results.append(alias)
    found = _fts(conn, tokens, "AND", limit + 1)
    if not found and not results:
        # Typos are common on phone keyboards ("chiken"); only try this when nothing matched.
        corrected = _spell_corrected(conn, tokens)
        if corrected != tokens:
            found = _fts(conn, corrected, "AND", limit + 1)
    if not found and not results and len(tokens) > 1:
        found = _fts(conn, tokens, "OR", limit + 1)
        for match in found:
            match.partial = True
    seen = {match.fdc_id for match in results}
    results.extend(match for match in found if match.fdc_id not in seen)
    results = results[:limit]
    for match in results:
        match.portions = get_portions(conn, match.fdc_id)
    return results
