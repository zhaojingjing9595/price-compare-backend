from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, HTTPException
from models.models import Product, Store
from schemas.schemas import ProductCreate, ProductResponse, SearchResultItem
from db.database import db_dependency
from sqlalchemy.exc import IntegrityError
from services.config import get_store_base_url
from services.products import search
from services.store_client import StoreUnavailableError, fetch_products

router = APIRouter()

@router.post("/products", response_model=ProductResponse)
async def register_product(product: ProductCreate, db: db_dependency):
    """Register a product for a store, seeding its price from the store's catalog.

    The price is looked up once here so the product is searchable immediately,
    without waiting for the next daily refresh.
    """
    store = db.get(Store, product.store_id)
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")

    base_url = get_store_base_url(store.name)
    if base_url is None:
        raise HTTPException(
            status_code=503,
            detail=f"No endpoint configured for store '{store.name}'",
        )

    try:
        catalog = await fetch_products(base_url, name_contains=product.name)
    except StoreUnavailableError as exc:
        raise HTTPException(
            status_code=503, detail=f"Store '{store.name}' is unavailable"
        ) from exc

    # name_contains is a substring filter, so confirm an exact match.
    listing = next((item for item in catalog if item["name"] == product.name), None)
    if listing is None:
        raise HTTPException(
            status_code=404,
            detail=f"Product '{product.name}' is not listed in store '{store.name}'",
        )

    db_product = Product(
        name=product.name,
        external_product_id=product.external_product_id,
        store_id=product.store_id,
        price=Decimal(str(listing["price"])),
        last_updated=datetime.now(),
    )
    db.add(db_product)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Product already registered for this store")
    db.refresh(db_product)
    return db_product


@router.get("/products", response_model=list[SearchResultItem])
def get_products(search_text: str, db: db_dependency):
    """Search the locally cached listings, cheapest first."""
    return [
        SearchResultItem(
            product_name=p.name,
            store_name=p.store.name,
            price=p.price,
            last_updated=p.last_updated,
        )
        for p in search(db, search_text)
    ]
