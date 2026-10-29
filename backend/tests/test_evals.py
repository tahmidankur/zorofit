import json

from app.services.llm.base import Interpretation
from evals.run_meal_evals import CASES, load_cases, score_case


def test_cases_file_is_valid_and_covers_categories():
    cases = load_cases(None)
    categories = {case["category"] for case in cases}

    assert 38 <= len(cases) <= 45
    assert {"single_item", "multi_item", "missing_quantity", "household_units", "typos", "regional",
            "correction", "confirm_plus_request", "out_of_scope"} <= categories
    assert len({case["id"] for case in cases}) == len(cases)


def test_scoring_a_perfect_answer(food_conn):
    case = json.loads(CASES.read_text().splitlines()[0])
    answer = Interpretation.model_validate(
        {"actions": [{"type": "log_meal", "items": [{"food": "banana", "quantity": 1, "unit": None}]}]}
    )

    score = score_case(food_conn, {**case, "expected": {**case["expected"], "items": [{"quantity": 1, "unit": None, "fdc_ids": [1008]}]}}, answer)

    assert score["intent"] and score["count"] and score["food"] == [True] and score["amount"] == [True]
