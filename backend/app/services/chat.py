"""The chat pipeline: safety check, interpretation, then one reply per action."""

import logging
import sqlite3
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.models import ChatMessage, Profile, Proposal
from app.services import meal_items, proposals, safety, workouts
from app.services.meals import today_for
from app.services.llm.base import Action, InterpretContext, Interpreter, InterpreterError
from app.services.llm.prompts import PROMPT_VERSION

FALLBACK_REPLY = "I couldn't read that one. You can add it by hand below."
NOTHING_PENDING = "There's no card waiting to be saved."
MAX_CHAT_REPLY = 400

logger = logging.getLogger("uvicorn.error")


@dataclass
class Reply:
    text: str
    proposal: Proposal | None = None
    fallback_query: str | None = None


@dataclass
class Turn:
    db: Session
    foods_db: sqlite3.Connection
    profile: Profile
    replies: list[Reply] = field(default_factory=list)

    @property
    def device_id(self) -> str:
        return self.profile.device_id


def build_context(turn: Turn) -> InterpretContext:
    pending = proposals.pending(turn.db, turn.device_id)
    last = proposals.last_saved_meal(turn.db, turn.device_id)
    last_summary = None
    if last:
        last_summary = ", ".join(f"{item.portion_text or str(item.grams) + ' g'} {item.food_name}" for item in last.items)
    return InterpretContext(
        pending_summary=proposals.summarize_items(pending.payload["items"]) if pending else None,
        last_meal_summary=last_summary,
    )


def meal_reply(items: list[dict]) -> str:
    unmatched = [item["query"] for item in items if item["unmatched"]]
    missing = [item["query"] for item in items if item["needs_portion"] and not item["unmatched"]]
    if unmatched:
        return f"I couldn't find {unmatched[0]} in the food list. Pick a close match, add it under My foods, or remove it."
    if len(missing) == 1:
        return f"How much {missing[0]} did you have?"
    if missing:
        return "How much of each did you have? Pick a portion on the card."
    return "Here's my estimate. Save it?"


def handle_log_meal(turn: Turn, action: Action) -> None:
    items = [
        meal_items.resolve_phrase(turn.db, turn.foods_db, turn.device_id, phrase.food, phrase.quantity, phrase.unit)
        for phrase in action.items or []
    ]
    if not items:
        turn.replies.append(Reply("What did you eat?"))
        return
    # Only one meal card is open at a time, so "yes" always means the newest one.
    proposals.discard_pending(turn.db, turn.device_id)
    proposal = proposals.create(
        turn.db, turn.device_id, "meal", proposals.meal_payload(items, action.meal_label), PROMPT_VERSION
    )
    turn.replies.append(Reply(meal_reply(items), proposal))


def handle_confirm(turn: Turn) -> None:
    pending = proposals.pending(turn.db, turn.device_id)
    if pending is None:
        turn.replies.append(Reply(NOTHING_PENDING))
        return
    if not proposals.can_save(pending.payload):
        turn.replies.append(Reply("Pick a portion for every item first, then save.", pending))
        return
    proposals.confirm(turn.db, turn.profile, pending.id)
    turn.replies.append(Reply("Saved.", pending))


def handle_discard(turn: Turn) -> None:
    if proposals.discard_pending(turn.db, turn.device_id):
        turn.replies.append(Reply("Discarded."))
    else:
        turn.replies.append(Reply(NOTHING_PENDING))


def apply_changes(turn: Turn, items: list[dict], action: Action) -> list[dict]:
    items = list(items)
    for change in action.changes or []:
        if change.op == "add":
            if change.food:
                items.append(
                    meal_items.resolve_phrase(
                        turn.db, turn.foods_db, turn.device_id, change.food, change.quantity, change.unit
                    )
                )
            continue
        target = meal_items.find_item(items, change.food)
        if target is None:
            continue
        index = items.index(target)
        if change.op == "remove":
            items.pop(index)
        elif change.quantity is not None:
            ref = meal_items.lookup_ref(turn.db, turn.foods_db, turn.device_id, target["key"])
            updated = meal_items.set_portion(target, ref, change.quantity, change.unit)
            if updated["grams"] is None and ref is None and target["per100"]:
                updated = meal_items.set_portion(target, None, change.quantity, change.unit)
            items[index] = updated
    return items


def handle_correct(turn: Turn, action: Action) -> None:
    pending = proposals.pending(turn.db, turn.device_id)
    if pending:
        items = apply_changes(turn, pending.payload["items"], action)
        if not items:
            proposals.discard_pending(turn.db, turn.device_id)
            turn.replies.append(Reply("That removes everything, so I discarded the card."))
            return
        pending.payload = {**pending.payload, "items": items}
        turn.replies.append(Reply("Updated. Save it?", pending))
        return

    last = proposals.last_saved_meal(turn.db, turn.device_id)
    if last is None:
        turn.replies.append(Reply("There's no meal to correct yet."))
        return
    current = [meal_items.item_from_saved(turn.db, turn.foods_db, turn.device_id, item) for item in last.items]
    items = apply_changes(turn, current, action)
    if not items:
        turn.replies.append(Reply("To remove the whole meal, delete it in History."))
        return
    proposal = proposals.create(
        turn.db, turn.device_id, "meal_edit", proposals.meal_payload(items, last.label, last.id), PROMPT_VERSION
    )
    turn.replies.append(Reply("Here's your last meal with that change. Save it?", proposal))


def handle_plan_workout(turn: Turn, action: Action) -> None:
    profile = turn.profile
    day = today_for(profile)
    minutes = min(max(action.minutes or profile.session_minutes, 10), 120)
    plan = workouts.plan_for(profile, day, minutes, action.focus)
    proposals.discard_pending(turn.db, turn.device_id, kinds=("workout",))
    proposal = proposals.create(
        turn.db, turn.device_id, "workout", {"workout": plan, "local_date": day.isoformat()}, PROMPT_VERSION
    )
    is_training_day = day.weekday() in profile.training_days
    what = "today's workout" if is_training_day else "a workout for today"
    turn.replies.append(Reply(f"Here's a {minutes}-minute version of {what}.", proposal))


def handle_action(turn: Turn, action: Action) -> None:
    if action.type == "log_meal":
        handle_log_meal(turn, action)
    elif action.type == "confirm_pending":
        handle_confirm(turn)
    elif action.type == "discard_pending":
        handle_discard(turn)
    elif action.type == "correct":
        handle_correct(turn, action)
    elif action.type == "plan_workout":
        handle_plan_workout(turn, action)
    elif action.type == "out_of_scope":
        turn.replies.append(Reply(safety.GENERAL_REPLY))
    else:
        text = (action.reply or "I can help you log meals and plan workouts.").strip()
        turn.replies.append(Reply(text[:MAX_CHAT_REPLY]))


def run(turn: Turn, message: str, interpreter: Interpreter) -> list[Reply]:
    fixed = safety.check(message)
    if fixed:
        return [Reply(fixed)]
    try:
        interpretation = interpreter.interpret(message, build_context(turn))
    except InterpreterError as error:
        logger.warning("interpreter failed: %s", error.reason)
        return [Reply(FALLBACK_REPLY, fallback_query=message)]
    # A medical message never also gets a meal or workout from the same turn.
    if any(action.type == "out_of_scope" for action in interpretation.actions):
        return [Reply(safety.GENERAL_REPLY)]
    for action in interpretation.actions:
        handle_action(turn, action)
    return turn.replies


def save_message(db: Session, device_id: str, role: str, text: str, proposal: Proposal | None = None) -> ChatMessage:
    message = ChatMessage(device_id=device_id, role=role, text=text, proposal_id=proposal.id if proposal else None)
    db.add(message)
    db.flush()
    return message
