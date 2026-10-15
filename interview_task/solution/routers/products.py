from fastapi import APIRouter, HTTPException, status
from sqlalchemy.exc import IntegrityError

from db.database import db_dependency
from models.models import Product, Store
from schemas.schemas import ProductCreate, ProductResponse, SearchResultItem
from services.search import search_products
from services.store_client import fetch_products
from services.sync import parse_listing

router = APIRouter(prefix="/products", tags=["products"])


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def register_product(product: ProductCreate, db: db_dependency):
    """Register a product for a store, seeding its price from the store's catalog
    so it is searchable immediately, without waiting for the next daily refresh.

    Store errors surface as 503 via the handlers in main.py.
    """
    store = await db.get(Store, product.store_id)
    if store is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Store not found")

    catalog = await fetch_products(store.api_endpoint, name_contains=product.name)
    # name_contains is a substring filter, so confirm an exact match.
    listing = next((item for item in catalog if item.get("name") == product.name), None)
    if listing is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            f"Product '{product.name}' is not listed in store '{store.name}'",
        )

    _, _, price = parse_listing(listing)
    db_product = Product(
        name=product.name,
        external_product_id=product.external_product_id,
        store_id=store.id,
        price=price,
    )
    db.add(db_product)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Product already registered for this store"
        )
    await db.refresh(db_product)
    return db_product


@router.get("", response_model=list[SearchResultItem])
async def search( db: db_dependency, search_text: str | None = None):
    """Search locally cached listings by name substring, cheapest first."""
    products = await search_products(db, search_text)
    return [
        SearchResultItem(
            product_name=p.name,
            store_name=p.store.name,
            price=p.price,
            last_updated=p.last_updated,
        )
        for p in products
    ]
