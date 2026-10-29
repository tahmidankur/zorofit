from tests.conftest import DEVICE_B, headers

EGGS = {"food_name": "Egg, whole", "portion_text": "2 large", "grams": 100, "kcal": 143, "protein_g": 12.6}
RICE = {"food_name": "Rice, white, cooked", "portion_text": "200 g", "grams": 200, "kcal": 260, "protein_g": 5.4}


def log_meal(client, items, eaten_at=None, tz="UTC", device=None):
    body = {"items": items, "label": "lunch"}
    if eaten_at:
        body["eaten_at"] = eaten_at
    kwargs = {"headers": headers(tz=tz) if device is None else headers(device, tz)}
    response = client.post("/api/meals", json=body, **kwargs)
    assert response.status_code == 201, response.text
    return response.json()


def test_today_totals_two_meals_against_targets(client):
    log_meal(client, [EGGS])
    log_meal(client, [RICE])

    today = client.get("/api/today", headers=headers()).json()

    assert today["totals"]["kcal"] == 403
    assert today["totals"]["protein_g"] == 18
    assert today["targets"] == {"kcal": 2000, "protein_g": 120}
    assert len(today["meals"]) == 2


def test_meal_at_2330_local_counts_toward_local_day(client):
    # 23:30 in Toronto on 10 March is 03:30 UTC on 11 March.
    meal = log_meal(client, [EGGS], eaten_at="2026-03-10T23:30:00-04:00", tz="America/Toronto")

    assert meal["local_date"] == "2026-03-10"
    assert meal["eaten_at"] == "2026-03-11T03:30:00Z"
    local_day = client.get("/api/today?date=2026-03-10", headers=headers(tz="America/Toronto")).json()
    utc_day = client.get("/api/today?date=2026-03-11", headers=headers(tz="America/Toronto")).json()
    assert len(local_day["meals"]) == 1
    assert utc_day["meals"] == []


def test_naive_eaten_at_is_rejected(client):
    response = client.post("/api/meals", json={"items": [EGGS], "eaten_at": "2026-03-10T12:00:00"}, headers=headers())

    assert response.status_code == 422


def test_delete_updates_today(client):
    meal = log_meal(client, [EGGS])
    log_meal(client, [RICE])

    assert client.delete(f"/api/meals/{meal['id']}", headers=headers()).status_code == 204
    assert client.get("/api/today", headers=headers()).json()["totals"]["kcal"] == 260


def test_edit_replaces_items(client):
    meal = log_meal(client, [EGGS])

    response = client.put(f"/api/meals/{meal['id']}", json={"label": "breakfast", "items": [RICE]}, headers=headers())

    assert response.status_code == 200
    assert response.json()["label"] == "breakfast"
    assert [item["food_name"] for item in response.json()["items"]] == ["Rice, white, cooked"]


def test_second_device_cannot_read_edit_or_delete_first_device_meals(client):
    meal = log_meal(client, [EGGS])
    other = headers(DEVICE_B)

    assert client.get("/api/meals", headers=other).json() == []
    assert client.get("/api/today", headers=other).json()["meals"] == []
    assert client.put(f"/api/meals/{meal['id']}", json={"items": [RICE]}, headers=other).status_code == 404
    assert client.delete(f"/api/meals/{meal['id']}", headers=other).status_code == 404
    assert len(client.get("/api/meals", headers=headers()).json()) == 1


def test_history_lists_newest_day_first(client):
    log_meal(client, [EGGS], eaten_at="2026-03-01T08:00:00Z")
    log_meal(client, [RICE], eaten_at="2026-03-03T08:00:00Z")

    days = [meal["local_date"] for meal in client.get("/api/meals", headers=headers()).json()]

    assert days == ["2026-03-03", "2026-03-01"]
