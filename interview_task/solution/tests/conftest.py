import asyncio
import os

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

# db.database reads DATABASE_URL at import time; tests never touch a real DB.
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite://")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool

from db.database import Base, get_db
from main import app
from models.models import Store

engine = create_async_engine(
    "sqlite+aiosqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,  # one shared in-memory DB across connections
)
TestingSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="session", autouse=True)
def _dispose_engine():
    yield
    # Plain (sync) fixture on purpose: it never touches anyio's per-test
    # event loop, so it's safe at session scope. asyncio.run() spins up a
    # throwaway loop just for this one call, after all tests have finished.
    asyncio.run(engine.dispose())


@pytest.fixture()
async def db_session(anyio_backend):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestingSessionLocal() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture()
async def client(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
async def store(db_session):
    store = Store(
        name="ebay",
        api_endpoint="http://ebay-server:9991/products",
        onboarded=True,
    )
    db_session.add(store)
    await db_session.commit()
    return store
