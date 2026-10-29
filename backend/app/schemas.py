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
    kcal: float
    protein_g: float


class TodayOut(BaseModel):
    date: date
    targets: Targets
    totals: Totals
    meals: list[MealOut]


class PortionChoice(BaseModel):
    label: str
    quantity: float
    unit: str
    grams: float


class FoodOut(BaseModel):
    key: str
    fdc_id: int | None
    custom_food_id: int | None
    name: str
    category: str
    kcal_100g: float
    protein_100g: float
    carbs_100g: float
    fat_100g: float
    portions: list[PortionChoice]


class CustomFoodIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    kcal_100g: float = Field(ge=0, le=900)
    protein_100g: float = Field(ge=0, le=100)
    carbs_100g: float = Field(0, ge=0, le=100)
    fat_100g: float = Field(0, ge=0, le=100)
    serving_name: str | None = Field(None, max_length=40)
    serving_grams: float | None = Field(None, gt=0, le=2000)


class CustomFoodOut(CustomFoodIn):
    model_config = ConfigDict(from_attributes=True)

    id: int


class FoodSummary(BaseModel):
    key: str | None
    name: str
    category: str


class ProposalItemOut(BaseModel):
    item_id: str
    query: str
    key: str | None
    food_name: str
    category: str
    quantity: float | None
    unit: str | None
    portion_text: str
    grams: float | None
    kcal: float | None
    protein_g: float | None
    carbs_g: float | None
    fat_g: float | None
    needs_portion: bool
    unmatched: bool
    portion_choices: list[PortionChoice]
    alternatives: list[FoodSummary]


class ProposalOut(BaseModel):
    id: str
    kind: str
    status: str
    label: str | None = None
    meal_id: int | None = None
    items: list[ProposalItemOut] = []
    totals: Targets | None = None
    can_save: bool
    duplicate_saved_at: UtcDatetime | None = None
    workout: dict | None = None


class ProposalItemEdit(BaseModel):
    item_id: str
    key: str | None = None
    grams: float | None = Field(None, gt=0, le=5000)
    portion_text: str | None = Field(None, max_length=60)
    kcal: float | None = Field(None, ge=0, le=10000)
    protein_g: float | None = Field(None, ge=0, le=1000)


class ProposalEdit(BaseModel):
    label: MealLabel | None = None
    items: list[ProposalItemEdit] = Field(min_length=1, max_length=20)


class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=1000)


class ChatMessageOut(BaseModel):
    id: int
    role: str
    text: str
    created_at: UtcDatetime
    proposal: ProposalOut | None = None
    fallback_query: str | None = None
