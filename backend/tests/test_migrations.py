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
    assert normalize_database_url("sqlite:///./liftfuel.db") == "sqlite:///./liftfuel.db"
