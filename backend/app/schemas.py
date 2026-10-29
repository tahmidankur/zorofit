from datetime import date, datetime, timezone
from typing import Annotated, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer, computed_field, field_validator


def _as_utc_string(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


# The DB stores naive UTC, so responses must say so or browsers read them as local time.
UtcDatetime = Annotated[datetime, PlainSerializer(_as_utc_string)]

Goal = Literal["lose", "maintain", "gain", "strength"]
MealLabel = Literal["breakfast", "lunch", "dinner", "snack"]
DietPref = Literal["vegetarian", "vegan", "pescatarian", "halal", "dairy_free", "gluten_free"]
Equipment = Literal["dumbbells", "barbell", "rack", "bench", "kettlebell", "pull_up_bar", "bands", "cable", "machines"]

CALORIE_MIN, CALORIE_MAX = 1200, 5000
PROTEIN_MIN, PROTEIN_MAX = 30, 300


def check_timezone(value: str) -> str:
    try:
        ZoneInfo(value)
    except (ZoneInfoNotFoundError, ValueError):
        raise ValueError("unknown timezone")
    return value


class ProfileIn(BaseModel):
    display_name: str = Field("", max_length=60)
    goal: Goal
    calorie_target: int = Field(ge=CALORIE_MIN, le=CALORIE_MAX)
    protein_target_g: int = Field(ge=PROTEIN_MIN, le=PROTEIN_MAX)
    diet_prefs: list[DietPref] = []
    equipment: list[Equipment] = []
    training_days: list[int] = []
    session_minutes: int = Field(ge=15, le=90)
    template_id: str = Field(max_length=40)
    timezone: str

    @field_validator("diet_prefs", "equipment")
    @classmethod
    def dedupe(cls, values: list[str]) -> list[str]:
        return sorted(set(values))

    @field_validator("training_days")
    @classmethod
    def check_days(cls, values: list[int]) -> list[int]:
        if any(day < 0 or day > 6 for day in values):
            raise ValueError("training days are weekday numbers 0 (Monday) to 6 (Sunday)")
        return sorted(set(values))

    @field_validator("timezone")
    @classmethod
    def valid_timezone(cls, value: str) -> str:
        return check_timezone(value)


class ProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    device_id: str
    display_name: str
    goal: Goal
    calorie_target: int
    protein_target_g: int
    diet_prefs: list[str]
    equipment: list[str]
    training_days: list[int]
    session_minutes: int
    template_id: str
    timezone: str


class MealItemIn(BaseModel):
    food_name: str = Field(min_length=1, max_length=200)
    portion_text: str = Field("", max_length=60)
    grams: float = Field(gt=0, le=5000)
    kcal: float = Field(ge=0, le=10000)
    protein_g: float = Field(ge=0, le=1000)
    carbs_g: float = Field(0, ge=0, le=1000)
    fat_g: float = Field(0, ge=0, le=1000)
    fdc_id: int | None = None
    custom_food_id: int | None = None


class MealIn(BaseModel):
    eaten_at: datetime | None = None
    label: MealLabel | None = None
    items: list[MealItemIn] = Field(min_length=1, max_length=20)

    @field_validator("eaten_at")
    @classmethod
    def needs_offset(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("eaten_at needs a timezone offset")
        return value


class MealItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    fdc_id: int | None
    custom_food_id: int | None
    food_name: str
    portion_text: str
    grams: float
    kcal: float
    protein_g: float
    carbs_g: float
    fat_g: float


class MealOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    eaten_at: UtcDatetime
    local_date: date
    label: str | None
    source: str
    items: list[MealItemOut]

    @computed_field
    @property
    def kcal(self) -> float:
        return round(sum(item.kcal for item in self.items), 1)

    @computed_field
    @property
    def protein_g(self) -> float:
        return round(sum(item.protein_g for item in self.items), 1)


class Totals(BaseModel):
    kcal: float
    protein_g: float
    carbs_g: float
    fat_g: float


class Targets(BaseModel):
    kcal: int
    protein_g: int


class TodayOut(BaseModel):
    date: date
    targets: Targets
    totals: Totals
    meals: list[MealOut]
