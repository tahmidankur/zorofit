import os
from dataclasses import dataclass
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# Free-tier quotas decide this: gemini-3.5-flash allows 20 requests a day, and 3.8-flash took over a minute per reply.
DEFAULT_GEMINI_MODEL = "gemini-3.5-flash-lite"
DEFAULT_GROQ_MODEL = "openai/gpt-oss-20b"


@dataclass(frozen=True)
class Settings:
    database_url: str
    frontend_origins: list[str]
    foods_db_path: Path
    llm_provider: str
    gemini_api_key: str
    gemini_model: str
    groq_api_key: str
    groq_model: str
    chat_limit_per_hour: int


def normalize_database_url(url: str) -> str:
    # Neon and Render hand out postgres:// URLs; SQLAlchemy needs the psycopg 3 driver named.
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    return url


def load_settings() -> Settings:
    return Settings(
        database_url=normalize_database_url(os.getenv("DATABASE_URL", "sqlite:///./zorofit.db")),
        frontend_origins=[
            origin.strip().rstrip("/")
            for origin in os.getenv("FRONTEND_ORIGIN", "http://localhost:5173").split(",")
            if origin.strip()
        ],
        foods_db_path=Path(os.getenv("FOODS_DB_PATH", DATA_DIR / "foods.db")),
        llm_provider=os.getenv("LLM_PROVIDER", "gemini").strip().lower(),
        gemini_api_key=os.getenv("GEMINI_API_KEY", "").strip(),
        gemini_model=os.getenv("GEMINI_MODEL", "").strip() or DEFAULT_GEMINI_MODEL,
        groq_api_key=os.getenv("GROQ_API_KEY", "").strip(),
        groq_model=os.getenv("GROQ_MODEL", "").strip() or DEFAULT_GROQ_MODEL,
        chat_limit_per_hour=int(os.getenv("CHAT_LIMIT_PER_HOUR", "40")),
    )


settings = load_settings()
