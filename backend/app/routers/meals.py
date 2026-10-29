from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db import get_db
from app.deps import get_profile
from app.models import Meal, Profile
from app.schemas import MealIn, MealOut
from app.services import meals as meal_service

router = APIRouter(prefix="/api/meals")


@router.get("", response_model=list[MealOut])
def list_meals(
    limit: int = Query(200, ge=1, le=500),
    profile: Profile = Depends(get_profile),
    db: Session = Depends(get_db),
):
    query = (
        select(Meal)
        .where(Meal.device_id == profile.device_id)
        .options(selectinload(Meal.items))
        .order_by(Meal.local_date.desc(), Meal.eaten_at.desc())
        .limit(limit)
    )
    return list(db.scalars(query))


@router.post("", response_model=MealOut, status_code=201)
def create_meal(body: MealIn, profile: Profile = Depends(get_profile), db: Session = Depends(get_db)):
    return meal_service.create_meal(db, profile, body.items, body.eaten_at, body.label, "manual")


@router.put("/{meal_id}", response_model=MealOut)
def update_meal(
    meal_id: int, body: MealIn, profile: Profile = Depends(get_profile), db: Session = Depends(get_db)
):
    meal = meal_service.get_meal(db, profile.device_id, meal_id)
    if body.eaten_at is not None:
        meal.eaten_at = meal_service.to_naive_utc(body.eaten_at)
        meal.local_date = meal_service.local_date_for(body.eaten_at, profile.timezone)
    meal.label = body.label
    meal.items = meal_service.build_items(body.items)
    db.commit()
    db.refresh(meal)
    return meal


@router.delete("/{meal_id}", status_code=204)
def delete_meal(meal_id: int, profile: Profile = Depends(get_profile), db: Session = Depends(get_db)):
    meal = meal_service.get_meal(db, profile.device_id, meal_id)
    db.delete(meal)
    db.commit()
