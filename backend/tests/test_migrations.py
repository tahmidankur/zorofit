from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import create_engine

from app.config import normalize_database_url
from app.db import Base
from app.migrate import alembic_config


def test_migrations_build_the_same_schema_as_the_models(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'app.db'}")
    config = alembic_config()
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "head")

    with engine.connect() as connection:
        differences = compare_metadata(MigrationContext.configure(connection), Base.metadata)

    assert differences == []


def test_postgres_urls_use_psycopg_driver():
    assert normalize_database_url("postgres://u:p@host/db") == "postgresql+psycopg://u:p@host/db"
    assert normalize_database_url("postgresql://u:p@host/db?sslmode=require") == "postgresql+psycopg://u:p@host/db?sslmode=require"
    assert normalize_database_url("sqlite:///./zorofit.db") == "sqlite:///./zorofit.db"


def test_config_description_never_includes_secrets(monkeypatch):
    from app import main
    from app.config import settings

    secret_settings = settings.__class__(
        **{**settings.__dict__, "database_url": "postgresql+psycopg://user:hunter2@db.example.com:5432/postgres", "gemini_api_key": "AIza-secret"}
    )
    monkeypatch.setattr(main, "settings", secret_settings)

    text = main.describe_config()

    assert "host=db.example.com" in text and "api_key_set=True" in text
    assert "hunter2" not in text and "AIza-secret" not in text
