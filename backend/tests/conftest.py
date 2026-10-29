from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models  # noqa: F401  registers tables on Base.metadata
from app.db import Base, get_db
from app.food_data import get_food_db
from app.main import app
from app.services.food_db import build_food_db, connect_read_only
from app.services.llm import get_interpreter
from tests.fake_interpreter import FakeInterpreter

DEVICE_A = "11111111-1111-4111-8111-111111111111"
DEVICE_B = "22222222-2222-4222-8222-222222222222"


def headers(device_id: str = DEVICE_A, tz: str = "UTC") -> dict:
    return {"X-Device-Id": device_id, "X-Timezone": tz}


@pytest.fixture
def db_session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    with Session() as session:
        yield session


FIXTURE_CSV_DIR = Path(__file__).parent / "fixtures" / "food_csv"


@pytest.fixture(scope="session")
def food_db_path(tmp_path_factory):
    path = tmp_path_factory.mktemp("foods") / "foods.db"
    build_food_db(FIXTURE_CSV_DIR, path)
    return path


@pytest.fixture
def food_conn(food_db_path):
    conn = connect_read_only(food_db_path)
    yield conn
    conn.close()


@pytest.fixture
def interpreter():
    return FakeInterpreter()


@pytest.fixture
def client(db_session, food_conn, interpreter):
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_food_db] = lambda: food_conn
    app.dependency_overrides[get_interpreter] = lambda: interpreter
    # Not used as a context manager, so the lifespan never touches the real database.
    yield TestClient(app)
    app.dependency_overrides.clear()
