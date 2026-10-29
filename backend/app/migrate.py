from pathlib import Path

from alembic import command
from alembic.config import Config

BACKEND_DIR = Path(__file__).resolve().parent.parent


def alembic_config() -> Config:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    # Absolute, so migrations run the same from any working directory (Render, tests, uvicorn).
    config.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    return config


def run_migrations() -> None:
    command.upgrade(alembic_config(), "head")
