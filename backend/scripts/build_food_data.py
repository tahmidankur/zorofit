"""Turn the raw USDA FoodData Central CSVs into the two trimmed files the app commits.

Usage: python scripts/build_food_data.py [raw_dir] [out_dir]
raw_dir holds one unzipped folder per dataset (foundation/, sr_legacy/).
"""

import csv
import sys
from pathlib import Path

DATASETS = {"foundation": "foundation_food", "sr_legacy": "sr_legacy_food"}

PROTEIN, FAT, CARBS = 1003, 1004, 1005
CARBS_BY_SUMMATION = 1050
# Foundation foods usually report Atwater energy instead of 1008.
ENERGY_IDS = (1008, 2047, 2048)
WANTED = {PROTEIN, FAT, CARBS, CARBS_BY_SUMMATION, *ENERGY_IDS}

SKIP_CATEGORIES = {"Baby Foods"}
UNDETERMINED_UNIT = "undetermined"

FOOD_FIELDS = ["fdc_id", "description", "data_type", "category", "kcal_100g", "protein_100g", "carbs_100g", "fat_100g"]
PORTION_FIELDS = ["fdc_id", "amount", "unit_name", "modifier", "gram_weight"]


def read_rows(path: Path):
    with path.open(newline="", encoding="utf-8") as handle:
        yield from csv.DictReader(handle)


def load_categories(folder: Path) -> dict[str, str]:
    return {row["id"]: row["description"] for row in read_rows(folder / "food_category.csv")}


def load_units(folder: Path) -> dict[str, str]:
    return {row["id"]: row["name"] for row in read_rows(folder / "measure_unit.csv")}


def load_foods(folder: Path, data_type: str, categories: dict[str, str]) -> dict[int, dict]:
    foods = {}
    for row in read_rows(folder / "food.csv"):
        if row["data_type"] != data_type:
            continue
        category = categories.get(row["food_category_id"], "")
        if category in SKIP_CATEGORIES:
            continue
        foods[int(row["fdc_id"])] = {
            "fdc_id": int(row["fdc_id"]),
            "description": row["description"].strip(),
            "data_type": data_type,
            "category": category,
        }
    return foods


def load_nutrients(folder: Path, fdc_ids: set[int]) -> dict[int, dict[int, float]]:
    values: dict[int, dict[int, float]] = {}
    for row in read_rows(folder / "food_nutrient.csv"):
        nutrient_id = int(row["nutrient_id"])
        if nutrient_id not in WANTED or not row["amount"]:
            continue
        fdc_id = int(row["fdc_id"])
        if fdc_id in fdc_ids:
            values.setdefault(fdc_id, {})[nutrient_id] = float(row["amount"])
    return values


def first_present(values: dict[int, float], ids) -> float | None:
    for nutrient_id in ids:
        if nutrient_id in values:
            return values[nutrient_id]
    return None


def food_row(food: dict, values: dict[int, float]) -> dict | None:
    kcal = first_present(values, ENERGY_IDS)
    if kcal is None:
        return None
    return {
        **food,
        "kcal_100g": round(kcal, 1),
        "protein_100g": round(values.get(PROTEIN, 0.0), 2),
        "carbs_100g": round(first_present(values, (CARBS, CARBS_BY_SUMMATION)) or 0.0, 2),
        "fat_100g": round(values.get(FAT, 0.0), 2),
    }


def portion_rows(folder: Path, fdc_ids: set[int], units: dict[str, str]):
    for row in read_rows(folder / "food_portion.csv"):
        # The 2026-04 Foundation release has a few hundred orphan rows with no fdc_id.
        if not row["fdc_id"] or not row["gram_weight"]:
            continue
        fdc_id = int(row["fdc_id"])
        if fdc_id not in fdc_ids:
            continue
        gram_weight = float(row["gram_weight"])
        amount = float(row["amount"]) if row["amount"] else 1.0
        if gram_weight <= 0 or amount <= 0:
            continue
        unit_name = units.get(row["measure_unit_id"], "")
        if unit_name == UNDETERMINED_UNIT:
            unit_name = ""
        # SR Legacy keeps the unit words in modifier; Foundation often uses portion_description.
        modifier = (row["modifier"] or row["portion_description"] or "").strip()
        if not unit_name and not modifier:
            continue
        yield {
            "fdc_id": fdc_id,
            "amount": round(amount, 3),
            "unit_name": unit_name,
            "modifier": modifier,
            "gram_weight": round(gram_weight, 2),
        }


def build(raw_dir: Path, out_dir: Path) -> tuple[int, int]:
    foods_out, portions_out = [], []
    for folder_name, data_type in DATASETS.items():
        folder = raw_dir / folder_name
        foods = load_foods(folder, data_type, load_categories(folder))
        nutrients = load_nutrients(folder, set(foods))
        kept = {}
        for fdc_id, food in foods.items():
            row = food_row(food, nutrients.get(fdc_id, {}))
            if row is not None:
                kept[fdc_id] = row
        foods_out.extend(kept.values())
        portions_out.extend(portion_rows(folder, set(kept), load_units(folder)))

    foods_out.sort(key=lambda row: row["fdc_id"])
    out_dir.mkdir(parents=True, exist_ok=True)
    write_csv(out_dir / "foods.csv", FOOD_FIELDS, foods_out)
    write_csv(out_dir / "portions.csv", PORTION_FIELDS, portions_out)
    return len(foods_out), len(portions_out)


def write_csv(path: Path, fields: list[str], rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    here = Path(__file__).resolve().parent.parent / "data"
    raw = Path(sys.argv[1]) if len(sys.argv) > 1 else here / "raw"
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else here
    food_count, portion_count = build(raw, out)
    print(f"wrote {food_count} foods and {portion_count} portions to {out}")
