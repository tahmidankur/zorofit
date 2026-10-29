from app.config import Settings, settings
from app.services.llm.base import Interpreter
from app.services.llm.gemini import GeminiInterpreter
from app.services.llm.groq import GroqInterpreter


def build_interpreter(config: Settings) -> Interpreter:
    if config.llm_provider == "groq":
        return GroqInterpreter(config.groq_api_key, config.groq_model)
    return GeminiInterpreter(config.gemini_api_key, config.gemini_model)


def get_interpreter() -> Interpreter:
    return build_interpreter(settings)
