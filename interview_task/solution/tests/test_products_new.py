"""POST /products — validation tests"""
from models.models import Product, Store

import pytest

def _fake_catalog(*items):
    async def fetch(_api_endpoint, _name_contains=None):
        return list(items)

    return fetch

def test_register_products_rejects_unknown_store(client):
    response = client.post(
        "/products",
        json={
            "name": "test_product",
            "external_product_id": "abcdef",
            "store_id": "123",
        })

    assert response.status_code == 404

@pytest.mark.anyio
async def test_register_products_rejects_unlisted_product(client, store, monkeypatch):
    monkeypatch.setattr(
        "routers.products.fetch_products",
        _fake_catalog({"name": "test_product", "external_product_id": "abcdef", "price": 1299.99}),
    )

    response = client.post(
        "/products",
        json={
            "name": "test_product99",
            "external_product_id": "abcdef99",
            "store_id": store.id,
        }
    )
    assert response.status_code == 404

@pytest.mark.anyio
async def test_register_products_rejects_duplicate(client, db_session, store, monkeypatch):
    monkeypatch.setattr(
        "routers.products.fetch_products",
        _fake_catalog({"name": "test_product", "external_product_id": "abcdef", "price": 1299.99}),
    )

    db_session.add(Product(name="test_product", store_id=store.id, price=1299.99))
    await db_session.commit()

    response = client.post(
        "/products",
        json={
            "name": "test_product",
            "external_product_id": "abcdef",
            "store_id": store.id,
        }
    )
    assert response.status_code == 409

@pytest.mark.anyio
async def test_register_products_accepted(client, db_session, store, monkeypatch):
    monkeypatch.setattr(
        "routers.products.fetch_products",
        _fake_catalog({"name": "test_product", "external_product_id": "abcdef", "price": 1299.99}),
    )

    response = client.post(
        "/products",
        json={
            "name": "test_product",
            "external_product_id": "abcdef",
            "store_id": store.id,
        }
    )
    assert response.status_code == 201


@pytest.mark.anyio
async def test_search_returns_cheapest_across_stores(client, db_session, store):
    other_store = Store(name="amazon", api_endpoint="http://amazon-server:9991/products", onboarded=True)
    db_session.add(other_store)
    await db_session.flush()

    db_session.add_all([
        Product(name="Laptop Pro", store_id=store.id, price=1299.99),
        Product(name="Laptop Pro", store_id=other_store.id, price=999.00),
    ])
    await db_session.commit()

    response = client.get(
        "/products",
        params={
            "search_text": "Laptop Pro"
        })
    assert [r["store_name"] for r in response.json()] == ["amazon", "ebay"]