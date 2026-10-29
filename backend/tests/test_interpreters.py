import json

import httpx
import pytest

from app.services.llm.base import InterpretContext, InterpreterError
from app.services.llm.gemini import GeminiInterpreter, to_gemini_schema
from app.services.llm.groq import GroqInterpreter
from app.services.llm.prompts import FEW_SHOTS, RESPONSE_SCHEMA, few_shot_turns
from app.services.llm.base import Interpretation

VALID = json.dumps(
    {"actions": [{"type": "log_meal", "items": [{"food": "egg", "quantity": 2, "unit": None}],
                  "meal_label": None, "changes": None, "minutes": None, "focus": None, "reply": None}]}
)


def gemini_reply(text: str) -> dict:
    return {"candidates": [{"content": {"parts": [{"text": text}]}}]}


def groq_reply(text: str) -> dict:
    return {"choices": [{"message": {"content": text}}]}


def transport(responses: list):
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(json.loads(request.content))
        status, body = responses.pop(0)
        return httpx.Response(status, json=body)

    return httpx.MockTransport(handler), calls


def test_few_shots_match_the_schema():
    for _, model_json in few_shot_turns():
        Interpretation.model_validate_json(model_json)
    assert 6 <= len(FEW_SHOTS) <= 8


def test_gemini_schema_uses_nullable_and_drops_additional_properties():
    converted = to_gemini_schema(RESPONSE_SCHEMA)
    action = converted["properties"]["actions"]["items"]

    assert action["properties"]["minutes"] == {"type": "integer", "nullable": True}
    assert "additionalProperties" not in action
    assert None not in action["properties"]["meal_label"]["enum"]


def test_gemini_sends_temperature_zero_and_schema():
    mock, calls = transport([(200, gemini_reply(VALID))])

    result = GeminiInterpreter("key", "model", mock).interpret("two eggs", InterpretContext())

    assert result.actions[0].items[0].food == "egg"
    config = calls[0]["generationConfig"]
    assert config["temperature"] == 0
    assert config["responseMimeType"] == "application/json"


@pytest.mark.parametrize("interpreter_class,reply", [(GeminiInterpreter, gemini_reply), (GroqInterpreter, groq_reply)])
def test_retries_once_on_invalid_json_then_succeeds(interpreter_class, reply):
    mock, calls = transport([(200, reply("not json")), (200, reply(VALID))])

    result = interpreter_class("key", "model", mock).interpret("two eggs", InterpretContext())

    assert len(calls) == 2
    assert result.actions[0].type == "log_meal"


@pytest.mark.parametrize("interpreter_class,reply", [(GeminiInterpreter, gemini_reply), (GroqInterpreter, groq_reply)])
def test_invalid_json_twice_raises(interpreter_class, reply):
    mock, _ = transport([(200, reply('{"actions": []}')), (200, reply("{}"))])

    with pytest.raises(InterpreterError) as error:
        interpreter_class("key", "model", mock).interpret("two eggs", InterpretContext())
    assert error.value.reason == "invalid_json"


@pytest.mark.parametrize("interpreter_class", [GeminiInterpreter, GroqInterpreter])
def test_429_raises_without_retry(interpreter_class):
    mock, calls = transport([(429, {"error": "quota"})])

    with pytest.raises(InterpreterError) as error:
        interpreter_class("key", "model", mock).interpret("two eggs", InterpretContext())
    assert error.value.reason == "rate_limited"
    assert len(calls) == 1


def test_timeout_raises():
    def handler(request):
        raise httpx.ReadTimeout("slow", request=request)

    with pytest.raises(InterpreterError) as error:
        GeminiInterpreter("key", "model", httpx.MockTransport(handler)).interpret("eggs", InterpretContext())
    assert error.value.reason == "timeout"


@pytest.mark.parametrize("interpreter_class", [GeminiInterpreter, GroqInterpreter])
def test_missing_key_raises_not_configured(interpreter_class):
    with pytest.raises(InterpreterError) as error:
        interpreter_class("", "model").interpret("two eggs", InterpretContext())
    assert error.value.reason == "not_configured"


def test_groq_uses_strict_json_schema():
    mock, calls = transport([(200, groq_reply(VALID))])

    GroqInterpreter("key", "openai/gpt-oss-20b", mock).interpret("two eggs", InterpretContext())

    assert calls[0]["response_format"]["json_schema"]["strict"] is True
    assert calls[0]["temperature"] == 0
