from app.models import Meal
from app.schemas import Totals


def day_totals(meals: list[Meal]) -> Totals:
    items = [item for meal in meals for item in meal.items]
    return Totals(
        kcal=round(sum(item.kcal for item in items), 1),
        protein_g=round(sum(item.protein_g for item in items), 1),
        carbs_g=round(sum(item.carbs_g for item in items), 1),
        fat_g=round(sum(item.fat_g for item in items), 1),
    )
