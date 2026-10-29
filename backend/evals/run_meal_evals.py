"""Run the meal cases against the real model. Uses API quota; run by hand, never in CI.

Usage: python -m evals.run_meal_evals [--provider gemini|groq] [--limit N]
"""

import argparse
import json
import time
from collections import defaultdict
from dataclasses import replace
from datetime import datetime
from pathlib import Path

from app.config import DATA_DIR, settings
from app.services.food_db import connect_read_only, ensure_food_db
from app.services.food_search import search
from app.services.llm import build_interpreter
from app.services.llm.base import InterpretContext, Interpretation, InterpreterError
from app.services.llm.prompts import PROMPT_VERSION
from app.services.portions import COUNT_WORDS, normalize_unit

HERE = Path(__file__).resolve().parent
CASES = HERE / "meal_cases.jsonl"
RESULTS = HERE / "results"
# Free tiers allow a handful of requests per minute.
PAUSE_SECONDS = 4.5


def load_cases(limit: int | None) -> list[dict]:
    cases = [json.loads(line) for line in CASES.read_text().splitlines() if line.strip()]
    return cases[:limit] if limit else cases


def same_unit(got: str | None, expected: str | None) -> bool:
    got_key, expected_key = normalize_unit(got), normalize_unit(expected)
    if got_key in COUNT_WORDS and expected_key in COUNT_WORDS:
        return True
    return got_key == expected_key


def same_quantity(got: float | None, expected: float | None) -> bool:
    if got is None or expected is None:
        return got is expected
    return abs(got - expected) < 1e-6


def food_matches(conn, food: str, expected: dict) -> bool:
    results = search(conn, food, 1)
    if expected.get("unmatched"):
        return not results or results[0].partial
    return bool(results) and not results[0].partial and results[0].fdc_id in expected["fdc_ids"]


def phrases(interpretation: Interpretation, action_type: str) -> list:
    found = []
    for action in interpretation.actions:
        if action.type == action_type:
            found.extend(action.items if action_type == "log_meal" else action.changes or [])
    return found


def score_case(conn, case: dict, interpretation: Interpretation | None) -> dict:
    expected = case["expected"]
    score = {"intent": False, "count": None, "food": [], "amount": [], "notes": []}
    if interpretation is None:
        score["notes"].append("model error")
        return score
    got_types = [action.type for action in interpretation.actions]
    score["intent"] = got_types == expected["actions"]
    if not score["intent"]:
        score["notes"].append(f"actions {got_types}")

    if "items" in expected:
        got = phrases(interpretation, "log_meal")
        score["count"] = len(got) == len(expected["items"])
        for phrase, wanted in zip(got, expected["items"]):
            score["food"].append(food_matches(conn, phrase.food, wanted))
            score["amount"].append(same_quantity(phrase.quantity, wanted["quantity"]) and same_unit(phrase.unit, wanted["unit"]))
            if not score["food"][-1]:
                top = search(conn, phrase.food, 1)
                score["notes"].append(f"'{phrase.food}' -> {top[0].description if top else 'nothing'}")
            if not score["amount"][-1]:
                score["notes"].append(f"'{phrase.food}' amount {phrase.quantity} {phrase.unit}")
    if "changes" in expected:
        got = phrases(interpretation, "correct")
        score["count"] = len(got) == len(expected["changes"])
        for change, wanted in zip(got, expected["changes"]):
            ok = change.op == wanted["op"] and same_quantity(change.quantity, wanted["quantity"]) and same_unit(change.unit, wanted["unit"])
            score["amount"].append(ok)
            if not ok:
                score["notes"].append(f"change {change.op} {change.quantity} {change.unit}")
    if "minutes" in expected:
        minutes = [action.minutes for action in interpretation.actions if action.type == "plan_workout"]
        ok = minutes == [expected["minutes"]]
        score["amount"].append(ok)
        if not ok:
            score["notes"].append(f"minutes {minutes}")
    return score


def rate(values: list[bool]) -> str:
    if not values:
        return "–"
    return f"{sum(values) / len(values):.0%} ({sum(values)}/{len(values)})"


def report(provider: str, model: str, cases: list[dict], scores: list[dict], elapsed: float) -> str:
    by_category = defaultdict(list)
    for case, score in zip(cases, scores):
        by_category[case["category"]].append(score)

    def summary(group: list[dict]) -> list[str]:
        return [
            rate([s["intent"] for s in group]),
            rate([s["count"] for s in group if s["count"] is not None]),
            rate([ok for s in group for ok in s["food"]]),
            rate([ok for s in group for ok in s["amount"]]),
        ]

    lines = [
        f"# Meal eval run {datetime.now():%Y-%m-%d %H:%M}",
        "",
        f"- Provider: {provider}, model: `{model}`",
        f"- Prompt version: `{PROMPT_VERSION}`",
        f"- Cases: {len(cases)}, time: {elapsed:.0f} s",
        "",
        "| Category | Intent | Item count | Food match | Quantity/unit |",
        "| --- | --- | --- | --- | --- |",
    ]
    for category, group in by_category.items():
        lines.append(f"| {category} | " + " | ".join(summary(group)) + " |")
    lines.append("| **All** | " + " | ".join(summary(scores)) + " |")
    lines += ["", "## Misses", ""]
    for case, score in zip(cases, scores):
        if score["notes"]:
            lines.append(f"- `{case['id']}` \"{case['message']}\": " + "; ".join(score["notes"]))
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", choices=["gemini", "groq"], default=settings.llm_provider)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()

    config = replace(settings, llm_provider=args.provider)
    model = config.groq_model if args.provider == "groq" else config.gemini_model
    interpreter = build_interpreter(config)
    ensure_food_db(DATA_DIR, config.foods_db_path)
    conn = connect_read_only(config.foods_db_path)

    cases = load_cases(args.limit)
    scores = []
    started = time.monotonic()
    for index, case in enumerate(cases):
        context = InterpretContext(case["context"]["pending"], case["context"]["last_meal"])
        try:
            interpretation = interpreter.interpret(case["message"], context)
        except InterpreterError as error:
            print(f"{case['id']}: {error.reason}")
            if error.reason == "not_configured":
                raise SystemExit(f"Set the API key for {args.provider} in backend/.env first.")
            interpretation = None
        scores.append(score_case(conn, case, interpretation))
        print(f"{index + 1}/{len(cases)} {case['id']}: {'ok' if not scores[-1]['notes'] else '; '.join(scores[-1]['notes'])}")
        time.sleep(PAUSE_SECONDS)

    text = report(args.provider, model, cases, scores, time.monotonic() - started)
    RESULTS.mkdir(exist_ok=True)
    path = RESULTS / f"{datetime.now():%Y-%m-%d-%H%M}-{args.provider}.md"
    path.write_text(text)
    print(text)
    print(f"Saved {path}")


if __name__ == "__main__":
    main()
