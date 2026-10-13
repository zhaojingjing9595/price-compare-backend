"""POST, GET /products — validation tests"""
from models.models import Product, Store
import pytest
from fastapi import status

PRODUCT_NAME = "test_product"
EXTERNAL_PRODUCT_ID = "test_external_product_id"
PRODUCT_PRICE = 999.99

def _fake_catalog(*items):
    async def fetch(api_endpoint, name_contains=None):
        return list(items)

    return fetch

def test_register_products_rejects_unknown_store(client):
    response = client.post(
        "/products",
        json={
            "name": PRODUCT_NAME,
            "external_product_id": EXTERNAL_PRODUCT_ID,
            "store_id": "123",
        })

    assert response.status_code == status.HTTP_404_NOT_FOUND

@pytest.mark.anyio
async def test_register_products_rejects_unlisted_product(client, ebay_store, monkeypatch):
    monkeypatch.setattr(
        "routers.products.fetch_products",
        _fake_catalog({"name": PRODUCT_NAME, "external_product_id": EXTERNAL_PRODUCT_ID, "price": PRODUCT_PRICE}),
    )

    response = client.post(
        "/products",
        json={
            "name": "test_product99",
            "external_product_id": "abcdef99",
            "store_id": ebay_store.id,
        }
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND

@pytest.mark.anyio
async def test_register_products_rejects_duplicate(client, db_session, ebay_store, monkeypatch):
    monkeypatch.setattr(
        "routers.products.fetch_products",
        _fake_catalog({"name": PRODUCT_NAME, "external_product_id": EXTERNAL_PRODUCT_ID, "price": PRODUCT_PRICE}),
    )

    db_session.add(Product(name=PRODUCT_NAME, store_id=ebay_store.id, price=PRODUCT_PRICE))
    await db_session.commit()

    response = client.post(
        "/products",
        json={
            "name": PRODUCT_NAME,
            "external_product_id": EXTERNAL_PRODUCT_ID,
            "store_id": ebay_store.id,
        }
    )
    assert response.status_code == status.HTTP_409_CONFLICT

@pytest.mark.anyio
async def test_register_products_accepted(client, db_session, ebay_store, monkeypatch):
    monkeypatch.setattr(
        "routers.products.fetch_products",
        _fake_catalog({"name": PRODUCT_NAME, "external_product_id": EXTERNAL_PRODUCT_ID, "price": PRODUCT_PRICE}),
    )

    response = client.post(
        "/products",
        json={
            "name": PRODUCT_NAME,
            "external_product_id": EXTERNAL_PRODUCT_ID,
            "store_id": ebay_store.id,
        }
    )
    assert response.status_code == status.HTTP_201_CREATED

@pytest.mark.anyio
async def test_search_returns_products_across_stores(client, db_session, ebay_store):
    amazon_store = Store(name="amazon", api_endpoint="http://amazon-server:9991/products", onboarded=True)
    db_session.add(amazon_store)
    await db_session.flush()

    db_session.add_all([
        Product(name="Laptop Pro", store_id=ebay_store.id, price=PRODUCT_PRICE),
        Product(name="Laptop Pro", store_id=amazon_store.id, price=999.00),
    ])
    await db_session.commit()

    response = client.get(
        "/products",
        params={
            "search_text": "Laptop"
        })
    assert response.status_code == status.HTTP_200_OK
    assert [r["store_name"] for r in response.json()] == ["amazon", "ebay"]