"""POST /stores — validation tests"""
import pytest

from models.models import Store


@pytest.mark.parametrize(
    "payload",
    [
        {"name": "etsy"},
        {"api_endpoint": "http://etsy/products"},
        {"name": "etsy", "api_endpoint": "not-a-url"},
    ]
)

def test_register_store_rejects_invalid_payload(client, payload):
    response = client.post("/stores", json=payload)

    assert response.status_code == 422

async def test_register_store_persists_expected_fields(client, db_session, monkeypatch):
    async def fake_cold_start(_store_id: int):
        pass

    monkeypatch.setattr("routers.stores.cold_start", fake_cold_start)

    response = client.post(
        "/stores",
        json={"name": "etsy", "api_endpoint": "http://etsy-server:8302/products"})

    store_id = response.json()["store_id"]

    stored = await db_session.get(Store, store_id)
    assert stored.name == "etsy"
    assert stored.api_endpoint == "http://etsy-server:8302/products"
    assert stored.onboarded is False

async def test_register_store_rejects_duplicate_store_name(client, store):
    response = client.post(
        "/stores",
        json={"name": store.name, "api_endpoint": "http://random-server/products"}
    )
    assert response.status_code == 409
