from pathlib import Path

from app.config import DATA_DIR
from app.services.food_db import build_food_db, connect_read_only
from app.services.food_search import search
from tests.conftest import DEVICE_B, headers


def test_alias_is_checked_before_full_text_search(food_conn):
    results = search(food_conn, "egg")

    assert results[0].description == "Egg, whole, raw, fresh"
    assert results[0].default_unit == "large"


def test_full_text_prefers_food_named_after_query(food_conn):
    results = search(food_conn, "chicken breast")

    assert results[0].fdc_id == 1006


def test_full_text_matches_plurals(food_conn):
    assert [match.fdc_id for match in search(food_conn, "bananas")][:1] == [1008]


def test_typo_falls_back_to_closest_spelling(food_conn):
    assert search(food_conn, "chiken brest")[0].fdc_id == 1006


def test_search_endpoint_returns_portions(client):
    results = client.get("/api/foods/search?q=rice", headers=headers()).json()

    assert results[0]["name"].startswith("Rice, white")
    assert results[0]["portions"][0] == {"label": "1 cup (158 g)", "quantity": 1, "unit": "cup", "grams": 158.0}


def test_custom_food_shows_in_search_and_can_be_logged(client):
    food = client.post(
        "/api/foods/custom",
        json={"name": "Chicken biryani", "kcal_100g": 180, "protein_100g": 9, "serving_name": "plate", "serving_grams": 350},
        headers=headers(),
    ).json()

    results = client.get("/api/foods/search?q=biryani", headers=headers()).json()
    assert results[0]["custom_food_id"] == food["id"]
    assert results[0]["portions"][0]["grams"] == 350

    meal = client.post(
        "/api/meals",
        json={"items": [{"food_name": "Chicken biryani", "custom_food_id": food["id"], "grams": 350, "kcal": 630, "protein_g": 31.5}]},
        headers=headers(),
    )
    assert meal.status_code == 201
    assert client.get("/api/foods/search?q=biryani", headers=headers(DEVICE_B)).json() == []


def test_custom_food_needs_serving_name_and_grams_together(client):
    response = client.post(
        "/api/foods/custom", json={"name": "Paratha", "kcal_100g": 300, "protein_100g": 6, "serving_grams": 80}, headers=headers()
    )

    assert response.status_code == 422


def test_rice_search_on_real_data_lists_cooked_white_rice_in_top_3(tmp_path: Path):
    db_path = tmp_path / "foods.db"
    build_food_db(DATA_DIR, db_path)
    conn = connect_read_only(db_path)

    names = [match.description for match in search(conn, "rice")[:3]]

    assert "Rice, white, long-grain, regular, enriched, cooked" in names
