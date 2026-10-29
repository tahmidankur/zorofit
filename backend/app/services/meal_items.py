"""Turns food phrases into card items: match a food, convert the portion, scale nutrition."""

import re
import sqlite3
import uuid
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.models import CustomFood, MealItem
from app.services import food_search
from app.services.custom_foods import custom_portions, search_custom_foods
from app.services.nutrition import scale_per_100g
from app.services.portions import PortionRow, portion_choices, to_grams

CANDIDATES = 5


@dataclass
class FoodRef:
    key: str | None
    fdc_id: int | None
    custom_food_id: int | None
    name: str
    category: str
    per100: dict
    portions: list[PortionRow] = field(default_factory=list)
    default_unit: str = ""
    partial: bool = False


def usda_ref(match: food_search.FoodMatch) -> FoodRef:
    return FoodRef(
        key=f"usda:{match.fdc_id}",
        fdc_id=match.fdc_id,
        custom_food_id=None,
        name=match.description,
        category=match.category,
        per100={"kcal": match.kcal_100g, "protein": match.protein_100g, "carbs": match.carbs_100g, "fat": match.fat_100g},
        portions=match.portions,
        default_unit=match.default_unit,
        partial=match.partial,
    )


def custom_ref(food: CustomFood) -> FoodRef:
    return FoodRef(
        key=f"custom:{food.id}",
        fdc_id=None,
        custom_food_id=food.id,
        name=food.name,
        category="My foods",
        per100={"kcal": food.kcal_100g, "protein": food.protein_100g, "carbs": food.carbs_100g, "fat": food.fat_100g},
        portions=custom_portions(food),
    )


def lookup_ref(db: Session, foods_db: sqlite3.Connection, device_id: str, key: str | None) -> FoodRef | None:
    if not key or ":" not in key:
        return None
    source, _, raw_id = key.partition(":")
    if not raw_id.isdigit():
        return None
    if source == "usda":
        match = food_search.get_food(foods_db, int(raw_id))
        return usda_ref(match) if match else None
    if source == "custom":
        food = db.get(CustomFood, int(raw_id))
        return custom_ref(food) if food and food.device_id == device_id else None
    return None


def find_candidates(db: Session, foods_db: sqlite3.Connection, device_id: str, query: str) -> list[FoodRef]:
    refs = [custom_ref(food) for food in search_custom_foods(db, device_id, query, limit=2)]
    refs += [usda_ref(match) for match in food_search.search(foods_db, query, CANDIDATES)]
    return refs[:CANDIDATES]


def summary(ref: FoodRef) -> dict:
    return {"key": ref.key, "name": ref.name, "category": ref.category}


def _with_grams(item: dict, grams: float | None, portion_text: str) -> dict:
    item = {**item, "grams": grams, "portion_text": portion_text, "needs_portion": grams is None}
    if grams is None:
        return {**item, "kcal": None, "protein_g": None, "carbs_g": None, "fat_g": None}
    per100 = item["per100"]
    values = scale_per_100g(grams, per100["kcal"], per100["protein"], per100["carbs"], per100["fat"])
    return {**item, **values}


def item_from_ref(ref: FoodRef, query: str, quantity: float | None, unit: str | None, alternatives: list[dict]) -> dict:
    item = {
        "item_id": uuid.uuid4().hex[:8],
        "query": query,
        "key": ref.key,
        "fdc_id": ref.fdc_id,
        "custom_food_id": ref.custom_food_id,
        "food_name": ref.name,
        "category": ref.category,
        "per100": ref.per100,
        "quantity": quantity,
        "unit": unit,
        "unmatched": False,
        "portion_choices": portion_choices(ref.portions),
        "alternatives": alternatives,
    }
    return set_portion(item, ref, quantity, unit)


def set_portion(item: dict, ref: FoodRef | None, quantity: float | None, unit: str | None) -> dict:
    portions = ref.portions if ref else []
    resolution = to_grams(portions, quantity, unit, item["food_name"], ref.default_unit if ref else "")
    return _with_grams({**item, "quantity": quantity, "unit": unit}, resolution.grams, resolution.portion_text)


def set_grams(item: dict, grams: float, portion_text: str | None = None) -> dict:
    return _with_grams(item, round(grams, 1), portion_text or f"{grams:g} g")


def unmatched_item(query: str, quantity: float | None, unit: str | None, alternatives: list[dict] | None = None) -> dict:
    return {
        "item_id": uuid.uuid4().hex[:8],
        "query": query,
        "key": None,
        "fdc_id": None,
        "custom_food_id": None,
        "food_name": query,
        "category": "",
        "per100": None,
        "quantity": quantity,
        "unit": unit,
        "unmatched": True,
        "needs_portion": True,
        "portion_text": "",
        "grams": None,
        "kcal": None,
        "protein_g": None,
        "carbs_g": None,
        "fat_g": None,
        "portion_choices": [],
        "alternatives": alternatives or [],
    }


def resolve_phrase(
    db: Session, foods_db: sqlite3.Connection, device_id: str, query: str, quantity: float | None, unit: str | None
) -> dict:
    candidates = find_candidates(db, foods_db, device_id, query)
    if not candidates:
        return unmatched_item(query, quantity, unit)
    if candidates[0].partial:
        return unmatched_item(query, quantity, unit, [summary(ref) for ref in candidates])
    best, others = candidates[0], candidates[1:]
    return item_from_ref(best, query, quantity, unit, [summary(ref) for ref in others])


def item_from_saved(db: Session, foods_db: sqlite3.Connection, device_id: str, saved: MealItem) -> dict:
    key = f"usda:{saved.fdc_id}" if saved.fdc_id else (f"custom:{saved.custom_food_id}" if saved.custom_food_id else None)
    ref = lookup_ref(db, foods_db, device_id, key)
    if ref is None:
        # A typed-in item has no reference food, so its own saved values stand in for per-100 g data.
        factor = 100 / saved.grams
        ref = FoodRef(
            key=None,
            fdc_id=None,
            custom_food_id=None,
            name=saved.food_name,
            category="",
            per100={
                "kcal": saved.kcal * factor,
                "protein": saved.protein_g * factor,
                "carbs": saved.carbs_g * factor,
                "fat": saved.fat_g * factor,
            },
        )
    item = item_from_ref(ref, saved.food_name, None, None, [])
    item["food_name"] = saved.food_name
    return set_grams(item, saved.grams, saved.portion_text)


def _words(text: str) -> set[str]:
    return {food_search.singular(word) for word in re.findall(r"[a-z]+", text.lower())}


def find_item(items: list[dict], food: str | None) -> dict | None:
    if not items:
        return None
    if not food:
        return items[0] if len(items) == 1 else None
    wanted = _words(food)
    best, best_score = None, 0
    for item in items:
        score = len(wanted & (_words(item["query"]) | _words(item["food_name"])))
        if score > best_score:
            best, best_score = item, score
    return best
