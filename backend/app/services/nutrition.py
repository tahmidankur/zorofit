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


def scale_per_100g(grams: float, kcal_100g: float, protein_100g: float, carbs_100g: float, fat_100g: float) -> dict:
    factor = grams / 100
    return {
        "kcal": round(kcal_100g * factor, 1),
        "protein_g": round(protein_100g * factor, 1),
        "carbs_g": round(carbs_100g * factor, 1),
        "fat_g": round(fat_100g * factor, 1),
    }
