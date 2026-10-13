"""POST /stores — validation tests"""
import pytest
from fastapi import status
from models.models import Store

STORE_NAME = "etsy"
STORE_API_ENDPOINT = "http://etsy-server:8302/products"

@pytest.mark.parametrize(
    "payload",
    [
        {"name": STORE_NAME},
        {"api_endpoint": STORE_API_ENDPOINT},
        {"name": STORE_NAME, "api_endpoint": "not-a-url"},
    ]
)
def test_register_store_rejects_invalid_payload(client, payload):
    response = client.post("/stores", json=payload)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


@pytest.mark.anyio
async def test_register_store_persists_expected_fields(client, db_session, monkeypatch):
    async def fake_cold_start(_store_id: int):
        pass

    monkeypatch.setattr("routers.stores.cold_start", fake_cold_start)

    response = client.post(
        "/stores",
        json={"name": STORE_NAME, "api_endpoint": STORE_API_ENDPOINT})

    assert response.status_code == status.HTTP_202_ACCEPTED
    store_id = response.json()["store_id"]

    stored = await db_session.get(Store, store_id)
    assert stored.name == STORE_NAME
    assert stored.api_endpoint == STORE_API_ENDPOINT
    assert stored.onboarded is False

@pytest.mark.anyio
async def test_register_store_rejects_duplicate_store_name(client, ebay_store):
    response = client.post(
        "/stores",
        json={"name": ebay_store.name, "api_endpoint": "http://random-server/products"}
    )
    assert response.status_code == status.HTTP_409_CONFLICT
