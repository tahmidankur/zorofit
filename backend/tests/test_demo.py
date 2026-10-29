from app.config import DATA_DIR
from app.services.demo import MENUS, demo_item
from app.services.food_db import build_food_db, connect_read_only
from app.food_data import get_food_db
from app.main import app
from tests.conftest import headers


def test_every_demo_item_resolves_on_real_food_data(tmp_path):
    db_path = tmp_path / "foods.db"
    build_food_db(DATA_DIR, db_path)
    conn = connect_read_only(db_path)

    missing = [phrase for menu in MENUS for phrases in menu.values() for phrase in phrases if demo_item(conn, *phrase) is None]

    assert missing == []


def test_demo_week_fills_history_once_and_keeps_real_entries(client, tmp_path):
    db_path = tmp_path / "foods.db"
    build_food_db(DATA_DIR, db_path)
    real_foods = connect_read_only(db_path)
    app.dependency_overrides[get_food_db] = lambda: real_foods
    client.put(
        "/api/profile",
        json={"display_name": "", "goal": "gain", "calorie_target": 2400, "protein_target_g": 150, "diet_prefs": [],
              "equipment": ["dumbbells"], "training_days": [0, 2, 4], "session_minutes": 45,
              "template_id": "full_body_a", "timezone": "UTC"},
        headers=headers(),
    )

    first = client.post("/api/demo", headers=headers()).json()
    second = client.post("/api/demo", headers=headers()).json()

    assert first["workouts_added"] >= 3
    assert second == {"meals_added": 0, "workouts_added": 0}
    days = {meal["local_date"] for meal in client.get("/api/meals", headers=headers()).json()}
    assert len(days) >= 6
    assert client.get("/api/workouts", headers=headers()).json()[0]["status"] in {"planned", "done", "skipped"}
