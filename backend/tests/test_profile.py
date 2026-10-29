import pytest

from tests.conftest import DEVICE_A, headers

VALID = {
    "display_name": "Sam",
    "goal": "gain",
    "calorie_target": 2600,
    "protein_target_g": 150,
    "diet_prefs": ["halal"],
    "equipment": ["dumbbells", "bench"],
    "training_days": [4, 0, 2],
    "session_minutes": 45,
    "template_id": "full_body_a",
    "timezone": "Asia/Dhaka",
}


def test_unknown_device_gets_default_profile_with_browser_timezone(client):
    response = client.get("/api/profile", headers=headers(tz="Europe/Berlin"))

    assert response.status_code == 200
    body = response.json()
    assert body["device_id"] == DEVICE_A
    assert body["timezone"] == "Europe/Berlin"
    assert body["calorie_target"] == 2000


def test_missing_or_bad_device_id_is_rejected(client):
    assert client.get("/api/profile").status_code == 422
    assert client.get("/api/profile", headers={"X-Device-Id": "abc"}).status_code == 400


def test_update_profile_saves_and_normalises_lists(client):
    response = client.put("/api/profile", json=VALID, headers=headers())

    assert response.status_code == 200
    assert response.json()["training_days"] == [0, 2, 4]
    assert client.get("/api/profile", headers=headers()).json()["goal"] == "gain"


@pytest.mark.parametrize(
    "field,value,ok",
    [
        ("calorie_target", 1199, False),
        ("calorie_target", 1200, True),
        ("calorie_target", 5000, True),
        ("calorie_target", 5001, False),
        ("protein_target_g", 29, False),
        ("protein_target_g", 30, True),
        ("protein_target_g", 300, True),
        ("protein_target_g", 301, False),
    ],
)
def test_target_ranges(client, field, value, ok):
    response = client.put("/api/profile", json={**VALID, field: value}, headers=headers())

    assert (response.status_code == 200) is ok


def test_rejects_unknown_timezone_and_weekday(client):
    assert client.put("/api/profile", json={**VALID, "timezone": "Mars/Base"}, headers=headers()).status_code == 422
    assert client.put("/api/profile", json={**VALID, "training_days": [7]}, headers=headers()).status_code == 422
