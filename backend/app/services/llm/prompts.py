import json

from app.services.llm.base import InterpretContext

PROMPT_VERSION = "meal-v2"

SYSTEM_PROMPT = """You are Zoro, the assistant inside ZoroFit, a food-logging and workout app.
You read the user's message and return JSON only, matching the schema. You never calculate calories,
protein, or grams; the app does all numbers.

Actions (one message can contain several, in the order the user said them):
- log_meal: the user ate or drank something. items is a list of {food, quantity, unit}.
  food: a short generic food name, keeping words that change nutrition ("cooked rice", "whole milk",
  "chicken biryani"). Fix obvious typos. Keep regional dish names as the user wrote them.
  quantity: a number exactly as stated ("two" -> 2, "half" -> 0.5, "a" or "an" -> 1). null if not stated.
  unit: the unit as stated, singular ("g", "kg", "oz", "cup", "tbsp", "slice", "large", "ml", "bowl").
  null if the user gave a count with no unit ("2 eggs"). Never invent a quantity or unit.
  meal_label: breakfast, lunch, dinner, or snack if the user said so, else null.
- confirm_pending: the user agrees to save the pending card ("yes", "save it", "looks right").
  Only when a pending card exists.
- discard_pending: the user wants the pending card thrown away. Only when a pending card exists.
- correct: the user changes the pending card, or the last saved meal if nothing is pending.
  changes is a list of {op: update | remove | add, food, quantity, unit}.
- plan_workout: the user wants a workout or says how much time they have. minutes if stated, focus if stated
  ("legs", "upper body"), else null.
- out_of_scope: injury, pain, illness, medication, pregnancy, disordered eating, or anything medical.
- chat: anything else about food or training. reply: one or two plain sentences, no emoji, no medical advice.
  For unrelated topics, reply that you can help with logging meals and planning workouts.

Unused fields are null."""


def action(type_: str, **fields) -> dict:
    base = {"type": type_, "items": None, "meal_label": None, "changes": None, "minutes": None, "focus": None, "reply": None}
    base.update(fields)
    return base


def item(food: str, quantity=None, unit=None) -> dict:
    return {"food": food, "quantity": quantity, "unit": unit}


def change(op: str, food=None, quantity=None, unit=None) -> dict:
    return {"op": op, "food": food, "quantity": quantity, "unit": unit}


FEW_SHOTS = [
    (
        InterpretContext(),
        "Zoro, I ate two eggs and 200 grams of cooked rice.",
        [action("log_meal", items=[item("egg", 2), item("cooked rice", 200, "g")])],
    ),
    (
        InterpretContext(),
        "had rice for lunch",
        [action("log_meal", items=[item("rice")], meal_label="lunch")],
    ),
    (
        InterpretContext(pending_summary="2 egg, 200 g cooked rice"),
        "Yes. I also only have 30 minutes to train today.",
        [action("confirm_pending"), action("plan_workout", minutes=30)],
    ),
    (
        InterpretContext(pending_summary="2 egg, 200 g cooked rice"),
        "actually it was 150 g of rice",
        [action("correct", changes=[change("update", "cooked rice", 150, "g")])],
    ),
    (
        InterpretContext(),
        "breakfast was 2 slices of toast with a tbsp of peanut butter and a banana",
        [
            action(
                "log_meal",
                items=[item("toast", 2, "slice"), item("peanut butter", 1, "tbsp"), item("banana", 1)],
                meal_label="breakfast",
            )
        ],
    ),
    (
        InterpretContext(pending_summary="1 cup oatmeal"),
        "nah scrap that",
        [action("discard_pending")],
    ),
    (
        InterpretContext(),
        "my knee clicks and aches when I squat, should I keep going?",
        [action("out_of_scope")],
    ),
    (
        InterpretContext(last_meal_summary="1 plate chicken biryani"),
        "what's a good snack after training?",
        [action("chat", reply="Something with protein and carbs works well, like yogurt with fruit or a sandwich with eggs.")],
    ),
]


def render_user_turn(message: str, context: InterpretContext) -> str:
    lines = [
        f"Pending card: {context.pending_summary or 'none'}",
        f"Last saved meal: {context.last_meal_summary or 'none'}",
        f"Message: {message}",
    ]
    return "\n".join(lines)


def few_shot_turns() -> list[tuple[str, str]]:
    return [(render_user_turn(text, context), json.dumps({"actions": actions})) for context, text, actions in FEW_SHOTS]


def _nullable(type_name: str) -> list[str]:
    return [type_name, "null"]


ITEM_SCHEMA = {
    "type": "object",
    "properties": {
        "food": {"type": "string"},
        "quantity": {"type": _nullable("number")},
        "unit": {"type": _nullable("string")},
    },
    "required": ["food", "quantity", "unit"],
    "additionalProperties": False,
}

CHANGE_SCHEMA = {
    "type": "object",
    "properties": {
        "op": {"type": "string", "enum": ["update", "remove", "add"]},
        "food": {"type": _nullable("string")},
        "quantity": {"type": _nullable("number")},
        "unit": {"type": _nullable("string")},
    },
    "required": ["op", "food", "quantity", "unit"],
    "additionalProperties": False,
}

RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "actions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "type": {
                        "type": "string",
                        "enum": ["log_meal", "confirm_pending", "discard_pending", "correct", "plan_workout", "out_of_scope", "chat"],
                    },
                    "items": {"type": _nullable("array"), "items": ITEM_SCHEMA},
                    "meal_label": {"type": _nullable("string"), "enum": ["breakfast", "lunch", "dinner", "snack", None]},
                    "changes": {"type": _nullable("array"), "items": CHANGE_SCHEMA},
                    "minutes": {"type": _nullable("integer")},
                    "focus": {"type": _nullable("string")},
                    "reply": {"type": _nullable("string")},
                },
                "required": ["type", "items", "meal_label", "changes", "minutes", "focus", "reply"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["actions"],
    "additionalProperties": False,
}
