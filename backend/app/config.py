import os
from dataclasses import dataclass
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


@dataclass(frozen=True)
class Settings:
    database_url: str
    frontend_origin: str
    foods_db_path: Path


def load_settings() -> Settings:
    return Settings(
        database_url=os.getenv("DATABASE_URL", "sqlite:///./liftfuel.db"),
        frontend_origin=os.getenv("FRONTEND_ORIGIN", "http://localhost:5173"),
        foods_db_path=Path(os.getenv("FOODS_DB_PATH", DATA_DIR / "foods.db")),
    )


settings = load_settings()
