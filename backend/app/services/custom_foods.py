import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CustomFood
from app.schemas import FoodOut, PortionChoice
from app.services.portions import PortionRow, portion_choices


def custom_portions(food: CustomFood) -> list[PortionRow]:
    if food.serving_name and food.serving_grams:
        return [PortionRow(1, "", food.serving_name, food.serving_grams)]
    return []


def custom_food_out(food: CustomFood) -> FoodOut:
    return FoodOut(
        key=f"custom:{food.id}",
        fdc_id=None,
        custom_food_id=food.id,
        name=food.name,
        category="My foods",
        kcal_100g=food.kcal_100g,
        protein_100g=food.protein_100g,
        carbs_100g=food.carbs_100g,
        fat_100g=food.fat_100g,
        portions=[PortionChoice(**choice) for choice in portion_choices(custom_portions(food))],
    )


def search_custom_foods(db: Session, device_id: str, text: str, limit: int = 3) -> list[CustomFood]:
    query = select(CustomFood).where(CustomFood.device_id == device_id)
    for token in re.findall(r"[\w]+", text.lower()):
        query = query.where(CustomFood.name.ilike(f"%{token}%"))
    return list(db.scalars(query.order_by(CustomFood.name).limit(limit)))
