"""Authorization (two devices) and abuse limits. Device ids are the only identity, so every id-taking
endpoint must refuse another device's records, and limits must not depend on ids a client can mint."""

import uuid

import pytest

from app.ratelimit import CHAT, NEW_DEVICES
from tests.conftest import DEVICE_A, DEVICE_B, headers

OWNER, INTRUDER = headers(DEVICE_A), headers(DEVICE_B)
EGGS = {"food_name": "Egg, whole", "portion_text": "2 large", "grams": 100, "kcal": 143, "protein_g": 12.6}
PROFILE = {
    "display_name": "Owner", "goal": "gain", "calorie_target": 2600, "protein_target_g": 150, "diet_prefs": [],
    "equipment": ["dumbbells"], "training_days": [0, 1, 2, 3, 4, 5, 6], "session_minutes": 45,
    "template_id": "full_body_a", "timezone": "UTC",
}


@pytest.fixture
def owned(client, interpreter):
    """One of every id-addressable resource, all belonging to DEVICE_A."""
    client.put("/api/profile", json=PROFILE, headers=OWNER)
    meal = client.post("/api/meals", json={"items": [EGGS]}, headers=OWNER).json()
    food = client.post("/api/foods/custom", json={"name": "Dal bhat", "kcal_100g": 120, "protein_100g": 5}, headers=OWNER).json()
    workout = client.get("/api/today", headers=OWNER).json()["workout"]
    interpreter.will_return({"type": "log_meal", "items": [{"food": "egg", "quantity": 2, "unit": None}]})
    card = client.post("/api/chat", json={"message": "two eggs"}, headers=OWNER).json()[1]["proposal"]
    return {"meal": meal, "food": food, "workout": workout, "card": card}


def attempts(owned):
    meal, food, workout, card = owned["meal"], owned["food"], owned["workout"], owned["card"]
    item_id = card["items"][0]["item_id"]
    return [
        ("PUT", f"/api/meals/{meal['id']}", {"items": [{**EGGS, "grams": 1, "kcal": 1, "protein_g": 1}]}),
        ("DELETE", f"/api/meals/{meal['id']}", None),
        ("DELETE", f"/api/foods/custom/{food['id']}", None),
        ("PUT", f"/api/workouts/{workout['id']}/status", {"status": "skipped"}),
        ("PUT", f"/api/proposals/{card['id']}", {"items": [{"item_id": item_id, "grams": 1}]}),
        ("POST", f"/api/proposals/{card['id']}/confirm", None),
        ("POST", f"/api/proposals/{card['id']}/discard", None),
    ]


def test_intruder_gets_404_on_every_owned_resource(client, owned):
    for method, path, body in attempts(owned):
        response = client.request(method, path, json=body, headers=INTRUDER)
        assert response.status_code == 404, (method, path, response.status_code)
        # The same answer as for a record that doesn't exist, so ids can't be probed.
        assert response.json()["detail"].endswith("not found")


def test_intruder_attempts_change_nothing(client, owned):
    for method, path, body in attempts(owned):
        client.request(method, path, json=body, headers=INTRUDER)

    meals = client.get("/api/meals", headers=OWNER).json()
    assert [m["items"][0]["grams"] for m in meals] == [100]
    assert [f["name"] for f in client.get("/api/foods/custom", headers=OWNER).json()] == ["Dal bhat"]
    assert client.get("/api/today", headers=OWNER).json()["workout"]["status"] == "planned"
    history = client.get("/api/chat", headers=OWNER).json()
    assert [m["proposal"]["status"] for m in history if m["proposal"]] == ["pending"]


def test_intruder_lists_none_of_the_owners_data(client, owned):
    assert client.get("/api/meals", headers=INTRUDER).json() == []
    assert client.get("/api/foods/custom", headers=INTRUDER).json() == []
    assert client.get("/api/chat", headers=INTRUDER).json() == []
    assert client.get("/api/workouts", headers=INTRUDER).json() == []
    assert client.get("/api/today", headers=INTRUDER).json()["meals"] == []
    assert all(food["custom_food_id"] is None for food in client.get("/api/foods/search?q=dal", headers=INTRUDER).json())
    assert client.get("/api/profile", headers=INTRUDER).json()["display_name"] == ""


def test_intruder_cannot_pull_owners_custom_food_into_own_card(client, owned, interpreter):
    interpreter.will_return({"type": "log_meal", "items": [{"food": "egg", "quantity": 2, "unit": None}]})
    card = client.post("/api/chat", json={"message": "two eggs"}, headers=INTRUDER).json()[1]["proposal"]
    item_id = card["items"][0]["item_id"]

    response = client.put(
        f"/api/proposals/{card['id']}",
        json={"items": [{"item_id": item_id, "key": f"custom:{owned['food']['id']}"}]},
        headers=INTRUDER,
    )

    assert response.status_code == 422


def test_owner_can_do_everything_the_intruder_could_not(client, owned):
    for method, path, body in attempts(owned):
        if path.endswith("/discard"):
            continue
        response = client.request(method, path, json=body, headers=OWNER)
        assert response.status_code in (200, 204), (method, path, response.status_code, response.text)


def test_requests_without_a_valid_device_id_are_refused(client):
    for path in ["/api/profile", "/api/meals", "/api/today", "/api/chat", "/api/workouts", "/api/foods/custom"]:
        assert client.get(path).status_code == 422
        assert client.get(path, headers={"X-Device-Id": "1 OR 1=1"}).status_code == 400


def test_new_devices_are_capped_per_network(client):
    for _ in range(NEW_DEVICES.limit):
        assert client.get("/api/profile", headers=headers(str(uuid.uuid4()))).status_code == 200

    blocked = client.get("/api/profile", headers=headers(str(uuid.uuid4())))

    assert blocked.status_code == 429
    assert client.get("/api/profile", headers=OWNER).status_code in (200, 429)


def test_chat_limit_follows_the_network_not_the_device_id(client, interpreter):
    for _ in range(CHAT.limit):
        interpreter.will_return({"type": "chat", "reply": "Hi."})
        device = headers(str(uuid.uuid4()))
        NEW_DEVICES.reset()
        assert client.post("/api/chat", json={"message": "hi"}, headers=device).status_code == 200

    NEW_DEVICES.reset()
    response = client.post("/api/chat", json={"message": "hi"}, headers=headers(str(uuid.uuid4())))

    assert response.status_code == 429
    assert len(interpreter.calls) == CHAT.limit


def test_spoofed_forwarded_for_does_not_reset_the_network_limit(client, interpreter):
    # Render keeps a client-sent X-Forwarded-For, so rotating it must not buy fresh limits.
    for index in range(CHAT.limit):
        interpreter.will_return({"type": "chat", "reply": "Hi."})
        NEW_DEVICES.reset()
        spoofed = {**headers(str(uuid.uuid4())), "X-Forwarded-For": f"198.51.100.{index}"}
        assert client.post("/api/chat", json={"message": "hi"}, headers=spoofed).status_code == 200

    NEW_DEVICES.reset()
    response = client.post(
        "/api/chat", json={"message": "hi"}, headers={**headers(str(uuid.uuid4())), "X-Forwarded-For": "198.51.100.250"}
    )

    assert response.status_code == 429


def test_cloudflare_client_ip_separates_networks(client, interpreter):
    interpreter.will_return({"type": "chat", "reply": "Hi."})
    for _ in range(CHAT.limit):
        CHAT.allow("203.0.113.1")

    blocked = client.post("/api/chat", json={"message": "hi"}, headers={**OWNER, "CF-Connecting-IP": "203.0.113.1"})
    allowed = client.post("/api/chat", json={"message": "hi"}, headers={**OWNER, "CF-Connecting-IP": "203.0.113.2"})

    assert blocked.status_code == 429
    assert allowed.status_code == 200


def test_daily_chat_cap_stops_model_calls_for_everyone(client, interpreter, monkeypatch):
    from app.config import settings
    from app.routers import chat as chat_router

    monkeypatch.setattr(chat_router, "settings", settings.__class__(**{**settings.__dict__, "chat_daily_limit": 2}))
    for device in (DEVICE_A, DEVICE_B):
        interpreter.will_return({"type": "chat", "reply": "Hi."})
        client.post("/api/chat", json={"message": "hi"}, headers=headers(device))

    response = client.post("/api/chat", json={"message": "hi"}, headers=headers(str(uuid.uuid4())))

    assert response.status_code == 429
    assert len(interpreter.calls) == 2


def test_demo_data_is_capped_per_network(client):
    statuses = [client.post("/api/demo", headers=OWNER).status_code for _ in range(6)]

    assert statuses[:5] == [200] * 5
    assert statuses[5] == 429


def test_oversized_and_unsized_bodies_are_rejected(client):
    big = "x" * (64 * 1024)
    assert client.post("/api/chat", content=f'{{"message": "{big}"}}', headers={**OWNER, "Content-Type": "application/json"}).status_code == 413

    def chunks():
        yield b'{"message": "hi"}'

    assert client.post("/api/chat", content=chunks(), headers={**OWNER, "Content-Type": "application/json"}).status_code == 411


@pytest.mark.parametrize("eaten_at", ["1999-01-01T08:00:00Z", "2999-01-01T08:00:00Z"])
def test_meal_dates_outside_the_past_year_are_rejected(client, eaten_at):
    response = client.post("/api/meals", json={"items": [EGGS], "eaten_at": eaten_at}, headers=OWNER)

    assert response.status_code == 422


def test_search_ignores_words_past_the_cap(food_conn):
    from app.services.food_search import MAX_QUERY_TOKENS, search

    long_query = "rice " + " ".join(f"zzword{n}" for n in range(200))

    assert len(long_query.split()) > MAX_QUERY_TOKENS
    search(food_conn, long_query)
