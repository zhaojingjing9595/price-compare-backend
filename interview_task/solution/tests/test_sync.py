"""The sync core shared by onboarding (cold start) and the daily refresh."""

from decimal import Decimal

import pytest

from models.models import Product, Store
from services import sync
from services.store_client import StoreUnavailableError


@pytest.mark.anyio
async def test_sync_store_upserts_and_marks_onboarded(db_session, monkeypatch):
    store = Store(name="ebay", api_endpoint="http://ebay/products", onboarded=False)
    db_session.add(store)
    db_session.commit()

    async def fetch(api_endpoint, name_contains=None):
        return [
            {"name": "Laptop", "external_product_id": "E-1", "price": 999},
            {"name": "broken"},  # malformed: skipped, not fatal
        ]

    monkeypatch.setattr(sync, "fetch_products", fetch)

    assert await sync.sync_store(db_session, store) == 1
    assert store.onboarded is True and store.last_synced_at is not None

    product = db_session.query(Product).filter_by(name="Laptop").one()
    assert product.price == Decimal("999")

    # A second sync updates in place rather than duplicating.
    await sync.sync_store(db_session, store)
    assert db_session.query(Product).count() == 1


@pytest.mark.anyio
async def test_cold_start_swallows_store_errors(db_session, monkeypatch):
    store = Store(name="ebay", api_endpoint="http://ebay/products", onboarded=False)
    db_session.add(store)
    db_session.commit()

    async def boom(api_endpoint, name_contains=None):
        raise StoreUnavailableError("down")

    monkeypatch.setattr(sync, "fetch_products", boom)
    monkeypatch.setattr(sync, "SessionLocal", lambda: _NoCloseSession(db_session))

    await sync.cold_start(store.id)  # must not raise
    assert store.onboarded is False  # retried by the daily refresh


class _NoCloseSession:
    """Wraps the test session so `with SessionLocal()` does not close it."""

    def __init__(self, session):
        self._session = session

    def __enter__(self):
        return self._session

    def __exit__(self, *exc):
        return False
