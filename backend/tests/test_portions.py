import pytest

from app.services.food_search import get_food
from app.services.nutrition import scale_per_100g
from app.services.portions import PortionRow, portion_choices, to_grams

EGG = [PortionRow(1, "", "large", 50), PortionRow(1, "", "medium", 44), PortionRow(1, "", "cup (4.86 large eggs)", 243)]
MILK = [PortionRow(1, "", "cup", 244), PortionRow(1, "", "fl oz", 30.5)]
PEANUT_BUTTER = [PortionRow(2, "tablespoon", "", 32)]
BREAD = [PortionRow(1, "", "slice", 25)]
BANANA = [PortionRow(1, "", 'medium (7" to 7-7/8" long)', 118), PortionRow(1, "", 'large (8" to 8-7/8" long)', 136)]
NO_PORTIONS: list[PortionRow] = []


@pytest.mark.parametrize(
    "quantity,unit,grams",
    [(150, "g", 150), (150, "grams", 150), (0.2, "kg", 200), (2, "oz", 56.7), (1, "lb", 453.6), (3, "Ounces", 85.0)],
)
def test_mass_units_convert_directly(quantity, unit, grams):
    assert to_grams(NO_PORTIONS, quantity, unit).grams == pytest.approx(grams, abs=0.1)


def test_household_unit_uses_portion_row():
    result = to_grams(EGG, 2, "large")

    assert result.grams == 100
    assert result.portion_text == "2 large"


@pytest.mark.parametrize("unit", ["slice", "slices", "Slice", "SLICES"])
def test_household_unit_ignores_case_and_plural(unit):
    assert to_grams(BREAD, 2, unit).grams == 50


def test_unit_abbreviation_matches_unit_name_and_divides_by_amount():
    assert to_grams(PEANUT_BUTTER, 1, "tbsp").grams == 16


def test_unit_matches_first_word_of_modifier():
    assert to_grams(EGG, 1, "cup").grams == 243


def test_ml_uses_density_from_volume_portion():
    # 244 g per cup of milk -> 250 ml weighs about 257.8 g.
    assert to_grams(MILK, 250, "ml").grams == pytest.approx(257.8, abs=0.1)


def test_ml_without_volume_portion_needs_portion():
    assert to_grams(BREAD, 250, "ml").needs_portion


def test_count_without_unit_uses_alias_default():
    result = to_grams(EGG, 2, None, "Egg, whole, raw, fresh", default_unit="large")

    assert result.grams == 100


def test_count_with_food_noun_as_unit_prefers_medium():
    assert to_grams(BANANA, 2, "bananas", "Bananas, raw").grams == 236


def test_missing_quantity_needs_portion():
    assert to_grams(EGG, None, "large").needs_portion


def test_unit_the_food_has_no_portion_for_needs_portion():
    assert to_grams(BREAD, 1, "cup").needs_portion


def test_unknown_unit_needs_portion_instead_of_guessing():
    assert to_grams(EGG, 1, "handful").needs_portion


def test_portion_choices_list_rows_then_100_g():
    choices = portion_choices(PEANUT_BUTTER)

    assert choices[0] == {"label": "1 tablespoon (16 g)", "quantity": 1, "unit": "tablespoon", "grams": 16.0}
    assert choices[-1]["label"] == "100 g"


def test_two_large_eggs_from_food_db_match_per_100g_values(food_conn):
    egg = get_food(food_conn, 1001)

    result = to_grams(egg.portions, 2, "large", egg.description)
    totals = scale_per_100g(result.grams, egg.kcal_100g, egg.protein_100g, egg.carbs_100g, egg.fat_100g)

    assert result.grams == 100
    assert totals["kcal"] == pytest.approx(result.grams * egg.kcal_100g / 100)
    assert totals["protein_g"] == pytest.approx(round(result.grams * egg.protein_100g / 100, 1))


def test_unit_matches_any_word_before_the_comma_in_modifier():
    potato = [PortionRow(1, "", "potato large", 299), PortionRow(1, "", "potato medium", 173)]

    assert to_grams(potato, 1, "medium").grams == 173
