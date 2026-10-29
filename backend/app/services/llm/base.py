from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, Field, ValidationError

ActionType = Literal["log_meal", "confirm_pending", "discard_pending", "correct", "plan_workout", "out_of_scope", "chat"]


class FoodPhrase(BaseModel):
    food: str = Field(min_length=1, max_length=120)
    quantity: float | None = None
    unit: str | None = Field(None, max_length=40)


class Change(BaseModel):
    op: Literal["update", "remove", "add"]
    food: str | None = Field(None, max_length=120)
    quantity: float | None = None
    unit: str | None = Field(None, max_length=40)


class Action(BaseModel):
    type: ActionType
    items: list[FoodPhrase] | None = None
    meal_label: Literal["breakfast", "lunch", "dinner", "snack"] | None = None
    changes: list[Change] | None = None
    minutes: int | None = None
    focus: str | None = Field(None, max_length=60)
    reply: str | None = Field(None, max_length=400)


class Interpretation(BaseModel):
    actions: list[Action] = Field(min_length=1, max_length=5)


@dataclass(frozen=True)
class InterpretContext:
    pending_summary: str | None = None
    last_meal_summary: str | None = None


class InterpreterError(Exception):
    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


def parse_interpretation(text: str) -> Interpretation:
    try:
        return Interpretation.model_validate_json(text)
    except ValidationError as error:
        raise InterpreterError("invalid_json") from error


class Interpreter(ABC):
    @abstractmethod
    def interpret(self, message: str, context: InterpretContext) -> Interpretation:
        """Raises InterpreterError when the provider can't give a valid interpretation."""
