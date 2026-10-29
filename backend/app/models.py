from datetime import date, datetime, timezone

from sqlalchemy import JSON, Date, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Profile(Base):
    __tablename__ = "profiles"

    device_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(60), default="")
    goal: Mapped[str] = mapped_column(String(10), default="maintain")
    calorie_target: Mapped[int] = mapped_column(Integer, default=2000)
    protein_target_g: Mapped[int] = mapped_column(Integer, default=120)
    diet_prefs: Mapped[list] = mapped_column(JSON, default=list)
    equipment: Mapped[list] = mapped_column(JSON, default=list)
    training_days: Mapped[list] = mapped_column(JSON, default=lambda: [0, 2, 4])
    session_minutes: Mapped[int] = mapped_column(Integer, default=45)
    template_id: Mapped[str] = mapped_column(String(40), default="full_body_a")
    timezone: Mapped[str] = mapped_column(String(64), default="UTC")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Meal(Base):
    __tablename__ = "meals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    device_id: Mapped[str] = mapped_column(String(36), index=True)
    # Stored as naive UTC; local_date is fixed at save time from the user's timezone.
    eaten_at: Mapped[datetime] = mapped_column(DateTime)
    local_date: Mapped[date] = mapped_column(Date, index=True)
    label: Mapped[str | None] = mapped_column(String(10), nullable=True)
    source: Mapped[str] = mapped_column(String(10), default="manual")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    items: Mapped[list["MealItem"]] = relationship(
        back_populates="meal", cascade="all, delete-orphan", order_by="MealItem.id"
    )


class MealItem(Base):
    __tablename__ = "meal_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    meal_id: Mapped[int] = mapped_column(ForeignKey("meals.id", ondelete="CASCADE"), index=True)
    fdc_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    custom_food_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    food_name: Mapped[str] = mapped_column(String(200))
    portion_text: Mapped[str] = mapped_column(String(60), default="")
    grams: Mapped[float] = mapped_column(Float)
    kcal: Mapped[float] = mapped_column(Float)
    protein_g: Mapped[float] = mapped_column(Float)
    carbs_g: Mapped[float] = mapped_column(Float, default=0)
    fat_g: Mapped[float] = mapped_column(Float, default=0)

    meal: Mapped[Meal] = relationship(back_populates="items")


class CustomFood(Base):
    __tablename__ = "custom_foods"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    device_id: Mapped[str] = mapped_column(String(36), index=True)
    name: Mapped[str] = mapped_column(String(120))
    kcal_100g: Mapped[float] = mapped_column(Float)
    protein_100g: Mapped[float] = mapped_column(Float)
    carbs_100g: Mapped[float] = mapped_column(Float, default=0)
    fat_100g: Mapped[float] = mapped_column(Float, default=0)
    serving_name: Mapped[str | None] = mapped_column(String(40), nullable=True)
    serving_grams: Mapped[float | None] = mapped_column(Float, nullable=True)
