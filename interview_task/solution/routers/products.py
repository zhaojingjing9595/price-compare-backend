from fastapi import APIRouter, HTTPException
from models.models import Product, Store
from schemas.schemas import ProductCreate, ProductResponse, SearchResultItem
from db.database import db_dependency
from sqlalchemy.exc import IntegrityError
from services.products import search

router = APIRouter()

@router.post("/products", response_model=ProductResponse)
def register_product(product: ProductCreate, db: db_dependency):
    store = db.get(Store, product.store_id)
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")

    db_product = Product(
        name=product.name, 
        external_product_id=product.external_product_id,
        store_id=product.store_id,
        price=product.price
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
async def get_products(search_text: str, db: db_dependency):
    products = search(db, search_text)
    
    results = [
        SearchResultItem(product_name=p.name, 
                         store_name=p.store.name, 
                         price=p.price, 
                         last_updated=p.last_updated) 
        for p in products
    ]
    
    return sorted(results, key=lambda r: r.price)
    
    