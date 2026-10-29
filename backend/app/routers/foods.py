import re
import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_profile
from app.food_data import get_food_db
from app.models import CustomFood, Profile
from app.schemas import CustomFoodIn, CustomFoodOut, FoodOut
from app.services import food_search
from app.services.custom_foods import custom_food_out, search_custom_foods
from app.services.portions import portion_choices

router = APIRouter(prefix="/api/foods")

SEARCH_LIMIT = 8


def usda_food_out(match: food_search.FoodMatch) -> FoodOut:
    return FoodOut(
        key=f"usda:{match.fdc_id}",
        fdc_id=match.fdc_id,
        custom_food_id=None,
        name=match.description,
        category=match.category,
        kcal_100g=match.kcal_100g,
        protein_100g=match.protein_100g,
        carbs_100g=match.carbs_100g,
        fat_100g=match.fat_100g,
        portions=portion_choices(match.portions),
    )


@router.get("/search", response_model=list[FoodOut])
def search_foods(
    q: str = Query(min_length=1, max_length=100),
    profile: Profile = Depends(get_profile),
    db: Session = Depends(get_db),
    foods_db: sqlite3.Connection = Depends(get_food_db),
):
    custom = [custom_food_out(food) for food in search_custom_foods(db, profile.device_id, q)]
    usda = [usda_food_out(match) for match in food_search.search(foods_db, q, SEARCH_LIMIT)]
    return (custom + usda)[:SEARCH_LIMIT]


@router.get("/custom", response_model=list[CustomFoodOut])
def list_custom_foods(profile: Profile = Depends(get_profile), db: Session = Depends(get_db)):
    query = select(CustomFood).where(CustomFood.device_id == profile.device_id).order_by(CustomFood.name)
    return list(db.scalars(query))


@router.post("/custom", response_model=CustomFoodOut, status_code=201)
def create_custom_food(body: CustomFoodIn, profile: Profile = Depends(get_profile), db: Session = Depends(get_db)):
    if (body.serving_name is None) != (body.serving_grams is None):
        raise HTTPException(status_code=422, detail="Give both a serving name and its grams, or neither")
    food = CustomFood(device_id=profile.device_id, **body.model_dump())
    food.name = re.sub(r"\s+", " ", food.name.strip())
    db.add(food)
    db.commit()
    return food


@router.delete("/custom/{food_id}", status_code=204)
def delete_custom_food(food_id: int, profile: Profile = Depends(get_profile), db: Session = Depends(get_db)):
    food = db.get(CustomFood, food_id)
    if food is None or food.device_id != profile.device_id:
        raise HTTPException(status_code=404, detail="Food not found")
    db.delete(food)
    db.commit()
