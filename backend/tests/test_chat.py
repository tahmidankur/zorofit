import pytest

from app.models import utcnow
from tests.conftest import DEVICE_B, headers


def log(food, quantity=None, unit=None):
    return {"food": food, "quantity": quantity, "unit": unit}


def send(client, message, device_headers=None):
    response = client.post("/api/chat", json={"message": message}, headers=device_headers or headers())
    assert response.status_code == 200, response.text
    return response.json()


def card(messages):
    return next(message["proposal"] for message in messages if message["proposal"])


def meals(client, device_headers=None):
    return client.get("/api/meals", headers=device_headers or headers()).json()


def test_eggs_and_rice_produce_card_with_totals_from_food_data(client, interpreter):
    interpreter.will_return({"type": "log_meal", "items": [log("egg", 2), log("cooked rice", 200, "g")]})

    messages = send(client, "Zoro, I ate two eggs and 200 grams of cooked rice.")

    assert [m["role"] for m in messages] == ["user", "zoro"]
    assert messages[1]["text"] == "Here's my estimate. Save it?"
    proposal = card(messages)
    eggs, rice = proposal["items"]
    assert (eggs["food_name"], eggs["grams"], eggs["portion_text"]) == ("Egg, whole, raw, fresh", 100, "2 large")
    assert (rice["grams"], rice["kcal"]) == (200, 260)
    assert proposal["totals"] == {"kcal": 403, "protein_g": 18}
    assert proposal["can_save"] is True
    assert meals(client) == []


def test_rice_without_amount_asks_how_much_with_portion_chips(client, interpreter):
    interpreter.will_return({"type": "log_meal", "items": [log("rice")], "meal_label": "lunch"})

    messages = send(client, "I had rice for lunch")

    assert messages[1]["text"] == "How much rice did you have?"
    item = card(messages)["items"][0]
    assert item["needs_portion"] is True
    assert [chip["label"] for chip in item["portion_choices"]] == ["1 cup (158 g)", "100 g"]
    assert card(messages)["can_save"] is False


def test_confirm_button_then_typed_yes_saves_one_meal(client, interpreter):
    interpreter.will_return({"type": "log_meal", "items": [log("egg", 2)]})
    proposal_id = card(send(client, "two eggs"))["id"]

    first = client.post(f"/api/proposals/{proposal_id}/confirm", headers=headers())
    second = client.post(f"/api/proposals/{proposal_id}/confirm", headers=headers())
    interpreter.will_return({"type": "confirm_pending"})
    typed = send(client, "yes")

    assert first.json()["status"] == second.json()["status"] == "confirmed"
    assert first.json()["meal_id"] == second.json()["meal_id"]
    assert typed[1]["text"] == "There's no card waiting to be saved."
    assert len(meals(client)) == 1
    assert meals(client)[0]["source"] == "chat"


def test_typed_yes_confirms_pending_card(client, interpreter):
    interpreter.will_return({"type": "log_meal", "items": [log("cooked rice", 150, "g")]})
    send(client, "150 g rice")
    interpreter.will_return({"type": "confirm_pending"})

    messages = send(client, "save it")

    assert messages[1]["text"] == "Saved."
    assert messages[1]["proposal"]["status"] == "confirmed"
    assert interpreter.calls[1][1].pending_summary == "150 g cooked rice"
    assert meals(client)[0]["items"][0]["grams"] == 150


def test_confirm_refuses_card_with_missing_portion(client, interpreter):
    interpreter.will_return({"type": "log_meal", "items": [log("rice")]})
    proposal_id = card(send(client, "rice"))["id"]

    response = client.post(f"/api/proposals/{proposal_id}/confirm", headers=headers())

    assert response.status_code == 422
    assert meals(client) == []


def test_picking_portion_chip_enables_save(client, interpreter):
    interpreter.will_return({"type": "log_meal", "items": [log("rice")]})
    proposal = card(send(client, "rice"))
    item = proposal["items"][0]

    edited = client.put(
        f"/api/proposals/{proposal['id']}",
        json={"label": "lunch", "items": [{"item_id": item["item_id"], "grams": 158, "portion_text": "1 cup"}]},
        headers=headers(),
    ).json()

    assert edited["items"][0]["kcal"] == pytest.approx(205.4)
    assert edited["can_save"] is True


def test_wrong_match_can_be_switched_to_another_option(client, interpreter):
    interpreter.will_return({"type": "log_meal", "items": [log("rice", 100, "g")]})
    proposal = card(send(client, "100 g rice"))
    item = proposal["items"][0]
    other = item["alternatives"][0]

    edited = client.put(
        f"/api/proposals/{proposal['id']}",
        json={"items": [{"item_id": item["item_id"], "key": other["key"]}]},
        headers=headers(),
    ).json()

    assert edited["items"][0]["key"] == other["key"]
    assert edited["items"][0]["grams"] == 100
    assert edited["items"][0]["alternatives"][0]["key"] == item["key"]


def test_unit_the_food_has_no_portion_for_asks_for_portion(client, interpreter):
    interpreter.will_return({"type": "log_meal", "items": [log("bread", 1, "cup")]})

    item = card(send(client, "a cup of bread"))["items"][0]

    assert item["needs_portion"] is True
    assert item["portion_choices"][0]["label"] == "1 slice (25 g)"


def test_correction_updates_pending_card(client, interpreter):
    interpreter.will_return({"type": "log_meal", "items": [log("egg", 2), log("cooked rice", 200, "g")]})
    send(client, "two eggs and 200 g rice")
    interpreter.will_return({"type": "correct", "changes": [{"op": "update", "food": "rice", "quantity": 150, "unit": "g"}]})

    messages = send(client, "actually it was 150 g of rice")

    assert messages[1]["text"] == "Updated. Save it?"
    assert [item["grams"] for item in card(messages)["items"]] == [100, 150]


def test_correction_after_save_opens_edit_card_for_last_meal(client, interpreter):
    interpreter.will_return({"type": "log_meal", "items": [log("cooked rice", 200, "g")]})
    proposal_id = card(send(client, "200 g rice"))["id"]
    client.post(f"/api/proposals/{proposal_id}/confirm", headers=headers())
    interpreter.will_return({"type": "correct", "changes": [{"op": "update", "food": "rice", "quantity": 150, "unit": "g"}]})

    edit = card(send(client, "actually it was 150 g"))
    client.post(f"/api/proposals/{edit['id']}/confirm", headers=headers())

    assert edit["kind"] == "meal_edit"
    saved = meals(client)
    assert len(saved) == 1
    assert saved[0]["items"][0]["grams"] == 150


def test_duplicate_within_15_minutes_is_flagged(client, interpreter):
    interpreter.will_return({"type": "log_meal", "items": [log("egg", 2)]})
    client.post(f"/api/proposals/{card(send(client, 'two eggs'))['id']}/confirm", headers=headers())
    interpreter.will_return({"type": "log_meal", "items": [log("egg", 2)]})

    again = card(send(client, "two eggs"))

    assert again["duplicate_saved_at"] is not None


def test_new_meal_replaces_previous_pending_card(client, interpreter):
    interpreter.will_return({"type": "log_meal", "items": [log("egg", 2)]})
    first = card(send(client, "two eggs"))
    interpreter.will_return({"type": "log_meal", "items": [log("banana", 1)]})
    send(client, "a banana")

    history = client.get("/api/chat", headers=headers()).json()
    statuses = [m["proposal"]["status"] for m in history if m["proposal"]]
    assert statuses == ["discarded", "pending"]
    assert first["id"] == history[1]["proposal"]["id"]


@pytest.mark.parametrize("reason", ["invalid_json", "rate_limited", "timeout", "not_configured"])
def test_model_failure_falls_back_to_manual_form(client, interpreter, reason):
    interpreter.will_fail(reason)

    messages = send(client, "two eggs")

    assert messages[1]["text"] == "I couldn't read that one. You can add it by hand below."
    assert messages[1]["fallback_query"] == "two eggs"


@pytest.mark.parametrize(
    "message",
    [
        "my shoulder hurts, can I still bench?",
        "I'm pregnant, what should I eat?",
        "should I take my medication before training",
        "I binged and want to purge",
        "I only have 30 minutes but my knee injury is acting up",
    ],
)
def test_out_of_scope_never_reaches_model_and_never_gives_workout(client, interpreter, message):
    messages = send(client, message)

    assert interpreter.calls == []
    assert len(messages) == 2
    assert messages[1]["proposal"] is None
    assert "doctor" in messages[1]["text"] or "physiotherapist" in messages[1]["text"]


def test_model_out_of_scope_drops_other_actions(client, interpreter):
    interpreter.will_return({"type": "out_of_scope"}, {"type": "log_meal", "items": [log("egg", 2)]})

    messages = send(client, "what supplements cure a cold")

    assert len(messages) == 2
    assert messages[1]["proposal"] is None


def test_other_device_cannot_confirm_or_see_cards(client, interpreter):
    interpreter.will_return({"type": "log_meal", "items": [log("egg", 2)]})
    proposal_id = card(send(client, "two eggs"))["id"]
    other = headers(DEVICE_B)

    assert client.post(f"/api/proposals/{proposal_id}/confirm", headers=other).status_code == 404
    assert client.get("/api/chat", headers=other).json() == []


def test_rate_limit_per_device(client, interpreter, monkeypatch):
    from app.routers import chat as chat_router
    from app.config import settings

    monkeypatch.setattr(chat_router, "settings", settings.__class__(**{**settings.__dict__, "chat_limit_per_hour": 2}))
    for _ in range(2):
        interpreter.will_return({"type": "chat", "reply": "Hi."})
        send(client, "hi")

    response = client.post("/api/chat", json={"message": "hi"}, headers=headers())

    assert response.status_code == 429
    assert client.post("/api/chat", json={"message": "my back hurts"}, headers=headers(DEVICE_B)).status_code == 200


def test_dish_missing_from_food_data_asks_user_to_pick_instead_of_guessing(client, interpreter):
    interpreter.will_return({"type": "log_meal", "items": [log("chicken biryani", 1, "plate")]})

    messages = send(client, "a plate of chicken biryani")
    item = card(messages)["items"][0]

    assert item["unmatched"] is True
    assert item["alternatives"][0]["name"].startswith("Chicken")
    assert "My foods" in messages[1]["text"]

    proposal = card(messages)
    edited = client.put(
        f"/api/proposals/{proposal['id']}",
        json={"items": [{"item_id": item["item_id"], "key": item["alternatives"][0]["key"], "grams": 300}]},
        headers=headers(),
    ).json()
    assert edited["can_save"] is True
