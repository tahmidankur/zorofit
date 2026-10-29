from datetime import date, timedelta

from tests.conftest import DEVICE_B, headers

PROFILE = {
    "display_name": "",
    "goal": "gain",
    "calorie_target": 2400,
    "protein_target_g": 150,
    "diet_prefs": [],
    "equipment": ["dumbbells", "bench"],
    "training_days": [0, 1, 2, 3, 4, 5, 6],
    "session_minutes": 60,
    "template_id": "full_body_a",
    "timezone": "UTC",
}


def set_profile(client, **changes):
    response = client.put("/api/profile", json={**PROFILE, **changes}, headers=headers())
    assert response.status_code == 200, response.text


def test_today_shows_planned_workout_on_training_day(client):
    set_profile(client)

    workout = client.get("/api/today", headers=headers()).json()["workout"]

    assert workout["status"] == "planned"
    assert workout["minutes_planned"] == 60
    assert workout["exercises"]["exercises"]


def test_no_workout_on_rest_day(client):
    rest_day = date(2026, 3, 10)
    set_profile(client, training_days=[(rest_day.weekday() + 1) % 7])

    assert client.get(f"/api/today?date={rest_day}", headers=headers()).json()["workout"] is None


def test_done_and_skip_update_status_for_owner_only(client):
    set_profile(client)
    workout = client.get("/api/today", headers=headers()).json()["workout"]

    done = client.put(f"/api/workouts/{workout['id']}/status", json={"status": "done"}, headers=headers())
    other = client.put(f"/api/workouts/{workout['id']}/status", json={"status": "skipped"}, headers=headers(DEVICE_B))

    assert done.json()["status"] == "done"
    assert other.status_code == 404
    assert client.get("/api/today", headers=headers()).json()["workout"]["status"] == "done"


def test_unknown_template_is_rejected(client):
    response = client.put("/api/profile", json={**PROFILE, "template_id": "nope"}, headers=headers())

    assert response.status_code == 422


def test_templates_are_listed(client):
    ids = [template["id"] for template in client.get("/api/workouts/templates").json()]

    assert ids == ["full_body_a", "full_body_b", "upper_lower", "bodyweight_quick"]


def test_chat_thirty_minutes_gives_card_and_use_this_replaces_todays_workout(client, interpreter):
    set_profile(client)
    planned = client.get("/api/today", headers=headers()).json()["workout"]
    interpreter.will_return({"type": "plan_workout", "minutes": 30})

    messages = client.post("/api/chat", json={"message": "I only have 30 minutes"}, headers=headers()).json()
    card = messages[1]["proposal"]

    assert messages[1]["text"] == "Here's a 30-minute version of today's workout."
    assert card["kind"] == "workout"
    assert card["workout"]["estimated_minutes"] <= 30
    assert client.get("/api/today", headers=headers()).json()["workout"]["minutes_planned"] == 60

    client.post(f"/api/proposals/{card['id']}/confirm", headers=headers())
    client.post(f"/api/proposals/{card['id']}/confirm", headers=headers())

    today = client.get("/api/today", headers=headers()).json()["workout"]
    assert today["id"] == planned["id"]
    assert today["minutes_planned"] == 30
    assert len(client.get("/api/workouts", headers=headers()).json()) == 1


def test_confirm_with_save_and_workout_in_one_message(client, interpreter):
    set_profile(client)
    interpreter.will_return({"type": "log_meal", "items": [{"food": "egg", "quantity": 2, "unit": None}]})
    client.post("/api/chat", json={"message": "two eggs"}, headers=headers())
    interpreter.will_return({"type": "confirm_pending"}, {"type": "plan_workout", "minutes": 30})

    messages = client.post("/api/chat", json={"message": "Yes. I also only have 30 minutes."}, headers=headers()).json()

    assert [m["text"] for m in messages[1:]] == ["Saved.", "Here's a 30-minute version of today's workout."]
    assert messages[2]["proposal"]["kind"] == "workout"
