import httpx

from app.services.llm.base import InterpretContext, Interpretation, Interpreter, InterpreterError, parse_interpretation
from app.services.llm.prompts import RESPONSE_SCHEMA, SYSTEM_PROMPT, few_shot_turns, render_user_turn

API_URL = "https://api.groq.com/openai/v1/chat/completions"
TIMEOUT_SECONDS = 15


class GroqInterpreter(Interpreter):
    def __init__(self, api_key: str, model: str, transport: httpx.BaseTransport | None = None):
        self.api_key = api_key
        self.model = model
        self.transport = transport

    def _request_body(self, message: str, context: InterpretContext) -> dict:
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        for user_text, model_json in few_shot_turns():
            messages.append({"role": "user", "content": user_text})
            messages.append({"role": "assistant", "content": model_json})
        messages.append({"role": "user", "content": render_user_turn(message, context)})
        return {
            "model": self.model,
            "messages": messages,
            "temperature": 0,
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": "interpretation", "strict": True, "schema": RESPONSE_SCHEMA},
            },
        }

    def _call(self, client: httpx.Client, body: dict) -> str:
        try:
            response = client.post(API_URL, headers={"Authorization": f"Bearer {self.api_key}"}, json=body)
        except httpx.TimeoutException as error:
            raise InterpreterError("timeout") from error
        except httpx.HTTPError as error:
            raise InterpreterError("network") from error
        if response.status_code == 429:
            raise InterpreterError("rate_limited")
        if response.status_code >= 400:
            raise InterpreterError(f"http_{response.status_code}")
        choices = response.json().get("choices") or []
        if not choices:
            raise InterpreterError("invalid_json")
        return choices[0].get("message", {}).get("content") or ""

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
