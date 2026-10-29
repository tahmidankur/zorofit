from datetime import date, timedelta

import pytest

from app.services.workout_gen import generate, load_exercises, load_templates

ALL_EQUIPMENT = ["dumbbells", "barbell", "rack", "bench", "kettlebell", "pull_up_bar", "bands", "cable", "machines"]
GOALS = ["lose", "maintain", "gain", "strength"]
DAY = date(2026, 3, 9)


def total_sets(workout: dict) -> int:
    return sum(exercise["sets"] for exercise in workout["exercises"])


def test_curated_data_is_about_sixty_exercises_covering_every_pattern():
    exercises = load_exercises()
    patterns = {exercise.pattern for exercise in exercises}

    assert 55 <= len(exercises) <= 65
    assert patterns == {"squat", "hinge", "lunge", "push_horizontal", "push_vertical", "pull_horizontal", "pull_vertical", "core", "carry"}


@pytest.mark.parametrize("template_id", list(load_templates()))
@pytest.mark.parametrize("equipment", [[], ["dumbbells", "bench"], ALL_EQUIPMENT])
def test_estimate_never_exceeds_requested_minutes(template_id, equipment):
    for minutes in range(15, 95, 5):
        for goal in GOALS:
            workout = generate(template_id, equipment, minutes, goal, DAY)
            assert workout["estimated_minutes"] * 60 <= minutes * 60 + 30, (template_id, minutes)
            assert 5 * 60 + sum(e["sets"] * (e["seconds_per_set"] + e["rest_seconds"]) for e in workout["exercises"]) <= minutes * 60
            assert workout["exercises"], (template_id, minutes)


@pytest.mark.parametrize("template_id", list(load_templates()))
def test_bodyweight_profile_never_gets_equipment(template_id):
    for offset in range(0, 70, 3):
        workout = generate(template_id, [], 60, "gain", DAY + timedelta(days=offset))
        assert all(exercise["equipment"] == [] for exercise in workout["exercises"])


def test_exercises_only_use_equipment_the_user_has():
    workout = generate("full_body_a", ["dumbbells"], 60, "gain", DAY)

    assert all(set(exercise["equipment"]) <= {"dumbbells"} for exercise in workout["exercises"])


def test_same_inputs_and_date_give_same_workout():
    first = generate("full_body_a", ALL_EQUIPMENT, 45, "strength", DAY)
    second = generate("full_body_a", ALL_EQUIPMENT, 45, "strength", DAY)

    assert first == second


def test_choices_rotate_from_week_to_week():
    names = {
        tuple(e["name"] for e in generate("full_body_a", ALL_EQUIPMENT, 60, "gain", DAY + timedelta(weeks=week))["exercises"])
        for week in range(4)
    }

    assert len(names) > 1


def test_longer_sessions_get_more_work_and_short_ones_keep_main_lifts():
    lengths = [20, 30, 45, 60]
    workouts = [generate("full_body_a", ALL_EQUIPMENT, minutes, "gain", DAY) for minutes in lengths]
    sets = [total_sets(workout) for workout in workouts]

    assert sets == sorted(sets)
    assert sets[0] < sets[-1]
    assert len(workouts[0]["exercises"]) < len(workouts[-1]["exercises"])
    assert workouts[0]["exercises"][0]["pattern"] == "squat"
    assert all(exercise["sets"] >= 2 for workout in workouts for exercise in workout["exercises"])


def test_reps_follow_goal():
    strength = generate("full_body_a", ALL_EQUIPMENT, 60, "strength", DAY)
    lose = generate("full_body_a", ALL_EQUIPMENT, 60, "lose", DAY)

    assert strength["exercises"][0]["reps"] == "4-6"
    assert lose["exercises"][0]["reps"] == "10-12"


def test_missing_equipment_for_a_pattern_is_reported():
    workout = generate("full_body_b", [], 60, "gain", DAY)

    assert "pull_vertical" in workout["skipped_patterns"]


def test_upper_lower_focus_picks_the_matching_day():
    legs = generate("upper_lower", ALL_EQUIPMENT, 60, "gain", DAY, focus="legs")
    upper = generate("upper_lower", ALL_EQUIPMENT, 60, "gain", DAY, focus="upper body")

    assert legs["exercises"][0]["pattern"] == "squat"
    assert upper["exercises"][0]["pattern"] == "push_horizontal"
