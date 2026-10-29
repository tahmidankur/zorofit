import re
from dataclasses import dataclass

GRAMS_PER_MASS_UNIT = {"g": 1.0, "kg": 1000.0, "oz": 28.3495, "lb": 453.592}
ML_PER_VOLUME_UNIT = {"ml": 1.0, "l": 1000.0, "cup": 236.588, "tablespoon": 14.787, "teaspoon": 4.929, "fl oz": 29.574}

UNIT_SYNONYMS = {
    "gram": "g", "grams": "g", "gr": "g", "gm": "g",
    "kilogram": "kg", "kilograms": "kg", "kgs": "kg",
    "ounce": "oz", "ounces": "oz",
    "pound": "lb", "pounds": "lb", "lbs": "lb",
    "milliliter": "ml", "millilitre": "ml", "milliliters": "ml", "millilitres": "ml", "mls": "ml",
    "liter": "l", "litre": "l", "liters": "l", "litres": "l",
    "tbsp": "tablespoon", "tbs": "tablespoon", "tbl": "tablespoon",
    "tsp": "teaspoon",
    "fluid ounce": "fl oz", "fl. oz": "fl oz",
}

# Words that mean "one of the thing itself" rather than a measured amount.
COUNT_WORDS = {"", "whole", "piece", "each", "item", "unit", "pc", "pcs", "x"}
COUNT_PREFERENCE = ("medium", "large", "whole", "small")


@dataclass(frozen=True)
class PortionRow:
    amount: float
    unit_name: str
    modifier: str
    gram_weight: float

    @property
    def grams_each(self) -> float:
        return self.gram_weight / self.amount

    @property
    def label(self) -> str:
        return " ".join(part for part in (self.unit_name, self.modifier) if part)


@dataclass(frozen=True)
class Resolution:
    grams: float | None
    portion_text: str

    @property
    def needs_portion(self) -> bool:
        return self.grams is None


def singular(word: str) -> str:
    if word.endswith("ies") and len(word) > 4:
        return word[:-3] + "y"
    if word.endswith(("ches", "shes", "oes")):
        return word[:-2]
    if word.endswith("s") and not word.endswith("ss") and len(word) > 2:
        return word[:-1]
    return word


def normalize_unit(unit: str | None) -> str:
    text = re.sub(r"\s+", " ", (unit or "").strip().lower().rstrip("."))
    if text in UNIT_SYNONYMS:
        return UNIT_SYNONYMS[text]
    if text in GRAMS_PER_MASS_UNIT or text in ML_PER_VOLUME_UNIT:
        return text
    one = singular(text)
    return UNIT_SYNONYMS.get(one, one)


def row_words(row: PortionRow) -> set[str]:
    words = set()
    if row.unit_name:
        words.add(normalize_unit(row.unit_name))
    if row.modifier:
        modifier = row.modifier.lower()
        words.add(normalize_unit(modifier))
        first = re.split(r"[,(]", modifier, maxsplit=1)[0].strip()
        words.add(normalize_unit(first))
        # SR Legacy sometimes puts the food name first ("potato medium").
        words.update(normalize_unit(word) for word in first.split(" "))
    words.discard("")
    return words


def format_quantity(quantity: float) -> str:
    return f"{quantity:g}"


def _matching_row(portions: list[PortionRow], unit: str) -> PortionRow | None:
    for row in portions:
        if unit in row_words(row):
            return row
    return None


def _volume_ml_per_gram(portions: list[PortionRow]) -> float | None:
    for row in portions:
        for word in row_words(row):
            if word in ML_PER_VOLUME_UNIT:
                return (row.amount * ML_PER_VOLUME_UNIT[word]) / row.gram_weight
    return None


def _count_row(portions: list[PortionRow], default_unit: str) -> PortionRow | None:
    if default_unit:
        row = _matching_row(portions, normalize_unit(default_unit))
        if row:
            return row
    for preferred in COUNT_PREFERENCE:
        for row in portions:
            if preferred in row.modifier.lower().split():
                return row
    return None


def _from_row(quantity: float, row: PortionRow, word: str) -> Resolution:
    return Resolution(round(quantity * row.grams_each, 1), f"{format_quantity(quantity)} {word}")


def to_grams(
    portions: list[PortionRow],
    quantity: float | None,
    unit: str | None,
    description: str = "",
    default_unit: str = "",
) -> Resolution:
    if quantity is None or quantity <= 0:
        return Resolution(None, "")
    unit_key = normalize_unit(unit)

    if unit_key in GRAMS_PER_MASS_UNIT:
        grams = quantity * GRAMS_PER_MASS_UNIT[unit_key]
        return Resolution(round(grams, 1), f"{format_quantity(quantity)} {unit_key}")

    row = _matching_row(portions, unit_key) if unit_key else None
    if row:
        return _from_row(quantity, row, unit_key)

    if unit_key in ML_PER_VOLUME_UNIT:
        # Only a portion with a known volume tells us the food's density; without one, ask.
        ml_per_gram = _volume_ml_per_gram(portions)
        if ml_per_gram is None:
            return Resolution(None, "")
        grams = quantity * ML_PER_VOLUME_UNIT[unit_key] / ml_per_gram
        return Resolution(round(grams, 1), f"{format_quantity(quantity)} {unit_key}")

    description_words = {singular(word) for word in re.findall(r"[a-z]+", description.lower())}
    if unit_key in COUNT_WORDS or unit_key in description_words:
        row = _count_row(portions, default_unit)
        if row:
            return _from_row(quantity, row, normalize_unit(row.modifier.split(" ")[0]) or row.label)

    return Resolution(None, "")


def portion_choices(portions: list[PortionRow], limit: int = 6) -> list[dict]:
    choices, seen = [], set()
    for row in portions:
        label = row.label
        if label in seen:
            continue
        seen.add(label)
        grams = round(row.grams_each, 1)
        choices.append({"label": f"1 {label} ({grams:g} g)", "quantity": 1, "unit": label, "grams": grams})
        if len(choices) == limit:
            break
    choices.append({"label": "100 g", "quantity": 100, "unit": "g", "grams": 100.0})
    return choices
