import json
from dataclasses import dataclass
from datetime import date
from functools import lru_cache

from app.config import DATA_DIR

WARM_UP_SECONDS = 5 * 60
MIN_SETS = 2


@dataclass(frozen=True)
class Exercise:
    id: str
    name: str
    pattern: str
    equipment: tuple[str, ...]
    seconds_per_set: int


@lru_cache
def load_exercises() -> tuple[Exercise, ...]:
    raw = json.loads((DATA_DIR / "exercises.json").read_text())
    return tuple(
        Exercise(item["id"], item["name"], item["pattern"], tuple(item["equipment"]), item["seconds_per_set"]) for item in raw
    )


@lru_cache
def load_templates() -> dict[str, dict]:
    raw = json.loads((DATA_DIR / "workout_templates.json").read_text())
    return {template["id"]: template for template in raw}


LOWER_FOCUS = ("leg", "lower", "glute", "squat")
UPPER_FOCUS = ("upper", "chest", "back", "arm", "shoulder", "push", "pull")


def pick_day(template: dict, day: date, focus: str | None = None) -> int:
    days = template["days"]
    if len(days) == 2 and focus:
        text = focus.lower()
        if any(word in text for word in LOWER_FOCUS):
            return 1
        if any(word in text for word in UPPER_FOCUS):
            return 0
    return day.toordinal() % len(days)


def choose_exercise(pattern: str, equipment: set[str], day: date, slot_index: int) -> Exercise | None:
    candidates = [e for e in load_exercises() if e.pattern == pattern and set(e.equipment) <= equipment]
    # Someone with a barbell should get barbell work, not air squats; bodyweight moves are the fallback.
    loaded = [e for e in candidates if e.equipment]
    pool = loaded or candidates
    if not pool:
        return None
    year, week, _ = day.isocalendar()
    return pool[(year * 53 + week + slot_index) % len(pool)]


def slot_seconds(entry: dict) -> int:
    return entry["sets"] * (entry["seconds_per_set"] + entry["rest_seconds"])


def estimate_seconds(entries: list[dict]) -> int:
    return WARM_UP_SECONDS + sum(slot_seconds(entry) for entry in entries)


def fit_to_time(entries: list[dict], limit_seconds: int) -> list[dict]:
    entries = [dict(entry) for entry in entries]
    by_lowest_priority = sorted(entries, key=lambda e: (-e["priority"], -entries.index(e)))

    for entry in by_lowest_priority:
        if estimate_seconds(entries) <= limit_seconds:
            return entries
        if entry["priority"] > 1:
            entries.remove(entry)

    while estimate_seconds(entries) > limit_seconds:
        reducible = [entry for entry in entries if entry["sets"] > MIN_SETS]
        if not reducible:
            break
        max(reducible, key=lambda e: (e["sets"], e["priority"]))["sets"] -= 1

    # Very short sessions can still be over after trimming sets; keep dropping, but never to nothing.
    while estimate_seconds(entries) > limit_seconds and len(entries) > 1:
        entries.remove(max(entries, key=lambda e: (e["priority"], entries.index(e))))
    return entries


def generate(
    template_id: str, equipment: list[str], minutes: int, goal: str, day: date, focus: str | None = None
) -> dict:
    template = load_templates()[template_id]
    available = set(equipment)
    entries, skipped = [], []
    slots = template["days"][pick_day(template, day, focus)]
    for index, slot in enumerate(slots):
        exercise = choose_exercise(slot["pattern"], available, day, index)
        if exercise is None:
            skipped.append(slot["pattern"])
            continue
        entries.append(
            {
                "id": exercise.id,
                "name": exercise.name,
                "pattern": slot["pattern"],
                "equipment": list(exercise.equipment),
                "sets": slot["sets"],
                "reps": slot["reps"][goal],
                "rest_seconds": slot["rest_seconds"],
                "seconds_per_set": exercise.seconds_per_set,
                "priority": slot["priority"],
            }
        )
    fitted = fit_to_time(entries, minutes * 60)
    return {
        "template_id": template_id,
        "template_name": template["name"],
        "minutes_planned": minutes,
        "estimated_minutes": round(estimate_seconds(fitted) / 60),
        "exercises": fitted,
        "skipped_patterns": skipped,
    }
