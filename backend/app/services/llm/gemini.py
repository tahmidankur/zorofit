import httpx

from app.services.llm.base import InterpretContext, Interpretation, Interpreter, InterpreterError, parse_interpretation
from app.services.llm.prompts import RESPONSE_SCHEMA, SYSTEM_PROMPT, few_shot_turns, render_user_turn

API_ROOT = "https://generativelanguage.googleapis.com/v1beta/models"
TIMEOUT_SECONDS = 15


def to_gemini_schema(schema: dict) -> dict:
    """Gemini's responseSchema is an OpenAPI subset: nullable instead of type lists, no additionalProperties."""
    converted = {}
    for key, value in schema.items():
        if key == "additionalProperties":
            continue
        if key == "type" and isinstance(value, list):
            converted["type"] = next(t for t in value if t != "null")
            converted["nullable"] = "null" in value
        elif key == "enum":
            converted["enum"] = [option for option in value if option is not None]
        elif key == "properties":
            converted["properties"] = {name: to_gemini_schema(sub) for name, sub in value.items()}
        elif key == "items":
            converted["items"] = to_gemini_schema(value)
        else:
            converted[key] = value
    return converted


class GeminiInterpreter(Interpreter):
    def __init__(self, api_key: str, model: str, transport: httpx.BaseTransport | None = None):
        self.api_key = api_key
        self.model = model
        self.transport = transport

    def _request_body(self, message: str, context: InterpretContext) -> dict:
        contents = []
        for user_text, model_json in few_shot_turns():
            contents.append({"role": "user", "parts": [{"text": user_text}]})
            contents.append({"role": "model", "parts": [{"text": model_json}]})
        contents.append({"role": "user", "parts": [{"text": render_user_turn(message, context)}]})
        return {
            "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
            "contents": contents,
            "generationConfig": {
                "temperature": 0,
                "responseMimeType": "application/json",
                "responseSchema": to_gemini_schema(RESPONSE_SCHEMA),
            },
        }

    def _call(self, client: httpx.Client, body: dict) -> str:
        try:
            response = client.post(
                f"{API_ROOT}/{self.model}:generateContent",
                headers={"x-goog-api-key": self.api_key},
                json=body,
            )
        except httpx.TimeoutException as error:
            raise InterpreterError("timeout") from error
        except httpx.HTTPError as error:
            raise InterpreterError("network") from error
        if response.status_code == 429:
            raise InterpreterError("rate_limited")
        if response.status_code >= 400:
            raise InterpreterError(f"http_{response.status_code}")
        data = response.json()
        candidates = data.get("candidates") or []
        if not candidates:
            raise InterpreterError("invalid_json")
        parts = candidates[0].get("content", {}).get("parts", [])
        return "".join(part.get("text", "") for part in parts)

    def interpret(self, message: str, context: InterpretContext) -> Interpretation:
        if not self.api_key:
            raise InterpreterError("not_configured")
        body = self._request_body(message, context)
        with httpx.Client(timeout=TIMEOUT_SECONDS, transport=self.transport) as client:
            try:
                return parse_interpretation(self._call(client, body))
            except InterpreterError as error:
                if error.reason != "invalid_json":
                    raise
            return parse_interpretation(self._call(client, body))
