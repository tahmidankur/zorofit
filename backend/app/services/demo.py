"""A filled-in week for people trying the app, built from the real food and workout data."""

import sqlite3
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Meal, Profile
from app.schemas import MealItemIn
from app.services import food_search, workouts
from app.services.meals import new_meal, today_for
from app.services.nutrition import scale_per_100g
from app.services.portions import to_grams

DAYS = 7
MEAL_TIMES = {"breakfast": time(8, 0), "lunch": time(13, 0), "snack": time(16, 0), "dinner": time(19, 30)}

MENUS = [
    {
        "breakfast": [("oats", 0.5, "cup"), ("milk", 1, "cup"), ("banana", 1, None)],
        "lunch": [("chicken breast", 150, "g"), ("rice", 1, "cup"), ("broccoli", 1, "cup")],
        "snack": [("greek yogurt", 170, "g"), ("almonds", 28, "g")],
        "dinner": [("salmon", 150, "g"), ("sweet potato", 1, "medium"), ("spinach", 1, "cup")],
    },
    {
        "breakfast": [("eggs", 3, None), ("toast", 2, "slice"), ("orange", 1, None)],
        "lunch": [("lentils", 1, "cup"), ("rice", 1, "cup"), ("cucumber", 100, "g")],
        "snack": [("peanut butter", 2, "tbsp"), ("apple", 1, None)],
        "dinner": [("ground beef", 120, "g"), ("pasta", 1, "cup"), ("tomato", 1, "medium")],
    },
    {
        "breakfast": [("greek yogurt", 200, "g"), ("blueberries", 1, "cup"), ("honey", 1, "tbsp")],
        "lunch": [("tuna", 140, "g"), ("bread", 2, "slice"), ("avocado", 100, "g")],
        "snack": [("protein powder", 30, "g"), ("milk", 1, "cup")],
        "dinner": [("tofu", 150, "g"), ("brown rice", 1, "cup"), ("broccoli", 1, "cup")],
    },
]


def demo_item(foods_db: sqlite3.Connection, phrase: str, quantity: float, unit: str | None) -> MealItemIn | None:
    match = food_search.alias_lookup(foods_db, phrase)
    if match is None:
        return None
    match.portions = food_search.get_portions(foods_db, match.fdc_id)
    resolution = to_grams(match.portions, quantity, unit, match.description, match.default_unit)
    if resolution.needs_portion:
        return None
    values = scale_per_100g(resolution.grams, match.kcal_100g, match.protein_100g, match.carbs_100g, match.fat_100g)
    return MealItemIn(
        food_name=match.description,
        portion_text=resolution.portion_text,
        grams=resolution.grams,
        fdc_id=match.fdc_id,
        **values,
    )


def days_with_meals(db: Session, device_id: str, days: list[date]) -> set[date]:
    query = select(Meal.local_date).where(Meal.device_id == device_id, Meal.local_date.in_(days))
    return set(db.scalars(query))


def load_demo_week(db: Session, foods_db: sqlite3.Connection, profile: Profile) -> dict:
    zone = ZoneInfo(profile.timezone)
    now = datetime.now(timezone.utc)
    today = today_for(profile)
    days = [today - timedelta(days=offset) for offset in range(DAYS - 1, -1, -1)]
    # Days that already have real entries are left alone; demo data only fills gaps.
    taken = days_with_meals(db, profile.device_id, days)
    meals_added = workouts_added = 0

    for index, day in enumerate(days):
        if day not in taken:
            menu = MENUS[day.toordinal() % len(MENUS)]
            for label, phrases in menu.items():
                eaten_at = datetime.combine(day, MEAL_TIMES[label], zone)
                if eaten_at > now:
                    continue
                items = [item for item in (demo_item(foods_db, *phrase) for phrase in phrases) if item]
                if items:
                    db.add(new_meal(profile, items, eaten_at, label, source="manual"))
                    meals_added += 1

        if day.weekday() in profile.training_days and workouts.workout_on(db, profile.device_id, day) is None:
            workout = workouts.save_plan(db, profile, day, workouts.plan_for(profile, day))
            if day < today:
                # One missed session makes the week look like a real one.
                workout.status = "skipped" if index == 1 else "done"
            workouts_added += 1

    db.commit()
    return {"meals_added": meals_added, "workouts_added": workouts_added}
