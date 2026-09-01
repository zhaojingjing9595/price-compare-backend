import os

# db.database reads DATABASE_URL at import time; tests never touch a real DB.
os.environ.setdefault("DATABASE_URL", "sqlite://")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from db.database import Base, get_db
from main import app
from models.models import Store

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,  # one shared in-memory DB across connections
)
TestingSessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture()
def db_session():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def store(db_session):
    store = Store(
        name="ebay",
        api_endpoint="http://ebay-server:9991/products",
        onboarded=True,
    )
    db_session.add(store)
    db_session.commit()
    return store
