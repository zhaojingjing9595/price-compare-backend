"""POST /products (registration) and GET /products (search)."""

from decimal import Decimal

import pytest

from models.models import Product
from services.store_client import StoreUnavailableError


def _fake_catalog(*items):
    async def fetch(api_endpoint, name_contains=None):
        return list(items)

    return fetch


def test_register_product_seeds_price_from_store(client, db_session, store, monkeypatch):
    monkeypatch.setattr(
        "routers.products.fetch_products",
        _fake_catalog({"name": "Laptop Pro", "external_product_id": "E-1", "price": 1299.99}),
    )

    resp = client.post(
        "/products",
        json={"name": "Laptop Pro", "external_product_id": "E-1", "store_id": store.id},
    )

    assert resp.status_code == 201
    assert Decimal(resp.json()["price"]) == Decimal("1299.99")


def test_register_product_not_listed_in_store(client, store, monkeypatch):
    # The store's substring filter matches, but no listing has the exact name.
    monkeypatch.setattr(
        "routers.products.fetch_products",
        _fake_catalog({"name": "Laptop Pro Max", "external_product_id": "E-2", "price": 10}),
    )

    resp = client.post(
        "/products",
        json={"name": "Laptop Pro", "external_product_id": "E-1", "store_id": store.id},
    )
    assert resp.status_code == 404


def test_register_product_store_unavailable_returns_503(client, store, monkeypatch):
    async def boom(api_endpoint, name_contains=None):
        raise StoreUnavailableError("connection refused")

    monkeypatch.setattr("routers.products.fetch_products", boom)

    resp = client.post(
        "/products",
        json={"name": "Laptop Pro", "external_product_id": "E-1", "store_id": store.id},
    )
    assert resp.status_code == 503


def test_search_returns_matches_cheapest_first(client, db_session, store):
    db_session.add_all(
        [
            Product(name="Laptop Pro", store_id=store.id, price=Decimal("1299.99")),
            Product(name="Laptop Air", store_id=store.id, price=Decimal("899.00")),
            Product(name="Coffee Mug", store_id=store.id, price=Decimal("9.00")),
        ]
    )
    db_session.commit()

    resp = client.get("/products", params={"search_text": "Laptop"})

    assert resp.status_code == 200
    results = resp.json()
    assert [r["product_name"] for r in results] == ["Laptop Air", "Laptop Pro"]
    assert all(r["store_name"] == store.name for r in results)


def test_search_with_no_matches_returns_empty_list(client, store):
    resp = client.get("/products", params={"search_text": "nothing-here"})
    assert resp.status_code == 200
    assert resp.json() == []
