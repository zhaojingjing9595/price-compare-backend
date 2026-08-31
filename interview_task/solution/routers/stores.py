from fastapi import APIRouter, HTTPException
from schemas.schemas import StoreCreate, StoreResponse, ProductCreate, ProductResponse
from db.database import db_dependency
from models.models import Store
from sqlalchemy.exc import IntegrityError

router = APIRouter()

@router.post("/stores", response_model=StoreResponse)
def register_store(store: StoreCreate, db: db_dependency):
    """Register a new store into database
    """
    db_store = Store(name=store.name)
    db.add(db_store)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail=f"Store '{store.name}' is already registered")

    db.refresh(db_store)
    return db_store

