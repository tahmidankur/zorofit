from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Meal, MealItem, Profile
from app.schemas import MealItemIn


def to_naive_utc(moment: datetime) -> datetime:
    return moment.astimezone(timezone.utc).replace(tzinfo=None)


def local_date_for(moment: datetime, tz_name: str) -> date:
    return moment.astimezone(ZoneInfo(tz_name)).date()


def today_for(profile: Profile) -> date:
    return local_date_for(datetime.now(timezone.utc), profile.timezone)


def build_items(items: list[MealItemIn]) -> list[MealItem]:
    return [MealItem(**item.model_dump()) for item in items]


def new_meal(
    profile: Profile,
    items: list[MealItemIn],
    eaten_at: datetime | None = None,
    label: str | None = None,
    source: str = "manual",
) -> Meal:
    eaten_at = eaten_at or datetime.now(timezone.utc)
    return Meal(
        device_id=profile.device_id,
        eaten_at=to_naive_utc(eaten_at),
        local_date=local_date_for(eaten_at, profile.timezone),
        label=label,
        source=source,
        items=build_items(items),
    )


def create_meal(
    db: Session,
    profile: Profile,
    items: list[MealItemIn],
    eaten_at: datetime | None = None,
    label: str | None = None,
    source: str = "manual",
) -> Meal:
    meal = new_meal(profile, items, eaten_at, label, source)
    db.add(meal)
    db.commit()
    db.refresh(meal)
    return meal


def get_meal(db: Session, device_id: str, meal_id: int) -> Meal:
    meal = db.get(Meal, meal_id)
    # Another device's meal gets the same 404 as a missing one, so ids can't be probed.
    if meal is None or meal.device_id != device_id:
        raise HTTPException(status_code=404, detail="Meal not found")
    return meal


def meals_on(db: Session, device_id: str, day: date) -> list[Meal]:
    query = (
        select(Meal)
        .where(Meal.device_id == device_id, Meal.local_date == day)
        .options(selectinload(Meal.items))
        .order_by(Meal.eaten_at)
    )
    return list(db.scalars(query))
