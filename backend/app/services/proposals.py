import sqlite3
import uuid
from datetime import datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import or_, select, update
from sqlalchemy.orm import Session, selectinload

from app.models import Meal, MealItem, Profile, Proposal, utcnow
from app.schemas import MealItemIn, ProposalEdit, ProposalOut
from app.services import meal_items
from app.services.meals import build_items, new_meal

DUPLICATE_WINDOW = timedelta(minutes=15)
MEAL_KINDS = ("meal", "meal_edit")


def create(db: Session, device_id: str, kind: str, payload: dict, prompt_version: str = "") -> Proposal:
    proposal = Proposal(
        id=str(uuid.uuid4()), device_id=device_id, kind=kind, payload=payload, prompt_version=prompt_version
    )
    db.add(proposal)
    db.flush()
    return proposal


def get_for_device(db: Session, device_id: str, proposal_id: str) -> Proposal:
    proposal = db.get(Proposal, proposal_id)
    if proposal is None or proposal.device_id != device_id:
        raise HTTPException(status_code=404, detail="Card not found")
    return proposal


def pending(db: Session, device_id: str, kinds=MEAL_KINDS) -> Proposal | None:
    query = (
        select(Proposal)
        .where(Proposal.device_id == device_id, Proposal.status == "pending", Proposal.kind.in_(kinds))
        .order_by(Proposal.created_at.desc())
        .limit(1)
    )
    return db.scalars(query).first()


def discard_pending(db: Session, device_id: str, kinds=MEAL_KINDS) -> int:
    result = db.execute(
        update(Proposal)
        .where(Proposal.device_id == device_id, Proposal.status == "pending", Proposal.kind.in_(kinds))
        .values(status="discarded", resolved_at=utcnow())
    )
    return result.rowcount


def can_save(payload: dict) -> bool:
    items = payload.get("items", [])
    return bool(items) and all(item["grams"] is not None and not item["unmatched"] for item in items)


def totals(items: list[dict]) -> dict:
    return {
        "kcal": round(sum(item["kcal"] or 0 for item in items), 1),
        "protein_g": round(sum(item["protein_g"] or 0 for item in items), 1),
    }


def recent_duplicate(db: Session, device_id: str, items: list[dict]) -> datetime | None:
    since = utcnow() - DUPLICATE_WINDOW
    latest = None
    for item in items:
        if item["grams"] is None:
            continue
        same_food = [MealItem.food_name == item["food_name"]]
        if item["fdc_id"]:
            same_food.append(MealItem.fdc_id == item["fdc_id"])
        if item["custom_food_id"]:
            same_food.append(MealItem.custom_food_id == item["custom_food_id"])
        query = (
            select(Meal.created_at)
            .join(MealItem, MealItem.meal_id == Meal.id)
            .where(
                Meal.device_id == device_id,
                Meal.created_at >= since,
                or_(*same_food),
                MealItem.grams.between(item["grams"] - 0.5, item["grams"] + 0.5),
            )
            .order_by(Meal.created_at.desc())
            .limit(1)
        )
        found = db.scalars(query).first()
        if found and (latest is None or found > latest):
            latest = found
    return latest


def to_out(db: Session, proposal: Proposal) -> ProposalOut:
    payload = proposal.payload
    if proposal.kind == "workout":
        return ProposalOut(
            id=proposal.id, kind=proposal.kind, status=proposal.status, can_save=True, workout=payload.get("workout")
        )
    items = payload.get("items", [])
    duplicate = None
    if proposal.kind == "meal" and proposal.status == "pending":
        duplicate = recent_duplicate(db, proposal.device_id, items)
    return ProposalOut(
        id=proposal.id,
        kind=proposal.kind,
        status=proposal.status,
        label=payload.get("label"),
        meal_id=payload.get("meal_id"),
        items=items,
        totals=totals(items),
        can_save=can_save(payload),
        duplicate_saved_at=duplicate,
    )


def summarize_items(items: list[dict]) -> str:
    parts = []
    for item in items:
        amount = item["portion_text"] or "? amount"
        parts.append(f"{amount} {item['query']}")
    return ", ".join(parts)


def meal_payload(items: list[dict], label: str | None, meal_id: int | None = None) -> dict:
    payload = {"label": label, "items": items}
    if meal_id is not None:
        payload["meal_id"] = meal_id
    return payload


def apply_edit(
    db: Session, foods_db: sqlite3.Connection, proposal: Proposal, body: ProposalEdit
) -> Proposal:
    if proposal.status != "pending" or proposal.kind not in MEAL_KINDS:
        raise HTTPException(status_code=409, detail="This card can no longer be changed")
    old_items = {item["item_id"]: item for item in proposal.payload["items"]}
    new_items = []
    for edit in body.items:
        item = old_items.get(edit.item_id)
        if item is None:
            raise HTTPException(status_code=422, detail=f"Unknown item {edit.item_id}")
        if edit.key and edit.key != item["key"]:
            item = switch_food(db, foods_db, proposal.device_id, item, edit.key)
        if edit.grams is not None:
            item = meal_items.set_grams(item, edit.grams, edit.portion_text)
        if edit.kcal is not None and item["grams"] is not None:
            item = {**item, "kcal": round(edit.kcal, 1)}
        if edit.protein_g is not None and item["grams"] is not None:
            item = {**item, "protein_g": round(edit.protein_g, 1)}
        new_items.append(item)
    proposal.payload = {**proposal.payload, "label": body.label, "items": new_items}
    db.commit()
    return proposal


def switch_food(db: Session, foods_db: sqlite3.Connection, device_id: str, item: dict, key: str) -> dict:
    ref = meal_items.lookup_ref(db, foods_db, device_id, key)
    if ref is None:
        raise HTTPException(status_code=422, detail="Unknown food")
    previous = [{"key": item["key"], "name": item["food_name"], "category": item["category"]}] if item["key"] else []
    alternatives = previous + [alt for alt in item["alternatives"] if alt["key"] != key]
    switched = meal_items.item_from_ref(ref, item["query"], item["quantity"], item["unit"], alternatives)
    if item["unmatched"]:
        switched["alternatives"] = [alt for alt in item["alternatives"] if alt["key"] != key]
    switched["item_id"] = item["item_id"]
    # Grams the user already chose stay put; the new food just changes the nutrition per gram.
    if item["grams"] is not None and switched["grams"] is None:
        switched = meal_items.set_grams(switched, item["grams"], item["portion_text"])
    return switched


def _items_in(items: list[dict]) -> list[MealItemIn]:
    return [
        MealItemIn(
            food_name=item["food_name"],
            portion_text=item["portion_text"][:60],
            grams=item["grams"],
            kcal=item["kcal"],
            protein_g=item["protein_g"],
            carbs_g=item["carbs_g"] or 0,
            fat_g=item["fat_g"] or 0,
            fdc_id=item["fdc_id"],
            custom_food_id=item["custom_food_id"],
        )
        for item in items
    ]


def confirm(db: Session, profile: Profile, proposal_id: str) -> Proposal:
    proposal = get_for_device(db, profile.device_id, proposal_id)
    if proposal.status == "confirmed":
        return proposal
    if proposal.status != "pending":
        raise HTTPException(status_code=409, detail="This card was discarded")
    if proposal.kind in MEAL_KINDS and not can_save(proposal.payload):
        raise HTTPException(status_code=422, detail="Every item needs a food and grams first")
    edited_meal = None
    if proposal.kind == "meal_edit":
        edited_meal = db.get(Meal, proposal.payload["meal_id"])
        if edited_meal is None or edited_meal.device_id != profile.device_id:
            raise HTTPException(status_code=409, detail="That meal was deleted")

    # The conditional update is the idempotency guard: of two racing confirms, only one changes a row.
    claimed = db.execute(
        update(Proposal)
        .where(Proposal.id == proposal.id, Proposal.status == "pending")
        .values(status="confirmed", resolved_at=utcnow())
    ).rowcount
    if claimed == 0:
        db.refresh(proposal)
        return proposal

    if proposal.kind == "meal":
        meal = new_meal(profile, _items_in(proposal.payload["items"]), label=proposal.payload.get("label"), source="chat")
        db.add(meal)
        db.flush()
        proposal.payload = {**proposal.payload, "meal_id": meal.id}
    elif proposal.kind == "meal_edit":
        edited_meal.items = build_items(_items_in(proposal.payload["items"]))
        edited_meal.label = proposal.payload.get("label")
    db.commit()
    db.refresh(proposal)
    return proposal


def discard(db: Session, device_id: str, proposal_id: str) -> Proposal:
    proposal = get_for_device(db, device_id, proposal_id)
    if proposal.status == "pending":
        proposal.status = "discarded"
        proposal.resolved_at = utcnow()
        db.commit()
    return proposal


def last_saved_meal(db: Session, device_id: str) -> Meal | None:
    query = (
        select(Meal)
        .where(Meal.device_id == device_id)
        .options(selectinload(Meal.items))
        .order_by(Meal.created_at.desc(), Meal.id.desc())
        .limit(1)
    )
    return db.scalars(query).first()
