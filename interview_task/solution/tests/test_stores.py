"""POST /stores — registration plus the background cold start."""

from models.models import Store


def test_register_store_accepts_and_schedules_backfill(client, db_session, monkeypatch):
    called = []

    async def fake_cold_start(store_id: int):
        called.append(store_id)

    monkeypatch.setattr("routers.stores.cold_start", fake_cold_start)

    resp = client.post(
        "/stores",
        json={"name": "ebay", "api_endpoint": "http://ebay-server:9991/products"},
    )

    assert resp.status_code == 202
    body = resp.json()
    assert body["name"] == "ebay" and body["status"] == "accepted"
    assert called == [body["store_id"]]

    stored = db_session.get(Store, body["store_id"])
    assert stored.api_endpoint == "http://ebay-server:9991/products"
    assert stored.onboarded is False  # only the backfill flips this


def test_register_store_rejects_duplicate(client, store):
    resp = client.post(
        "/stores",
        json={"name": store.name, "api_endpoint": store.api_endpoint},
    )
    assert resp.status_code == 409
