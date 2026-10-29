import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    database_url: str
    frontend_origin: str


def load_settings() -> Settings:
    return Settings(
        database_url=os.getenv("DATABASE_URL", "sqlite:///./zoro.db"),
        frontend_origin=os.getenv("FRONTEND_ORIGIN", "http://localhost:5173"),
    )


settings = load_settings()
