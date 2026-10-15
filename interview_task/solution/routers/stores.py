from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from sqlalchemy import select

from db.database import db_dependency
from models.models import Store
from schemas.schemas import RefreshResponse, StoreCreate, StoreOnboardResponse, StoreResponse
from services.sync import cold_start, refresh_all_stores, sync_store
router = APIRouter(prefix="/stores", tags=["stores"])


@router.get("", response_model=list[StoreResponse])
async def list_stores(db: db_dependency):
    """All registered stores."""
    result = await db.execute(select(Store))
    return result.scalars().all()

@router.post("", response_model=StoreOnboardResponse, status_code=status.HTTP_202_ACCEPTED)
async def register_store(store: StoreCreate, background_tasks: BackgroundTasks, db: db_dependency):
    """Register a store and kick off its catalog backfill.

    Registering — not the scheduler — is what fires the first fetch, so a new store
    is searchable in seconds instead of up to 24h later. The backfill runs in the
    background and the call returns 202 immediately.
    """
    existing = await db.execute(select(Store).filter_by(name=store.name))
    if existing.scalar_one_or_none():
        raise HTTPException(status.HTTP_409_CONFLICT, f"Store '{store.name}' is already registered")

    new_store = Store(name=store.name, api_endpoint=str(store.api_endpoint), onboarded=False)
    db.add(new_store)
    await db.commit()
    await db.refresh(new_store)

    background_tasks.add_task(cold_start, new_store.id)

    return StoreOnboardResponse(
        store_id=new_store.id,
        name=new_store.name,
        status="accepted",
        message="Store registered, catalog backfill started",
    )


@router.post("/refresh", response_model=RefreshResponse)
async def refresh_all():
    """Force-refresh every onboarded store now instead of waiting for the daily job."""
    return RefreshResponse(products_synced=await refresh_all_stores())


@router.post("/{store_id}/refresh", response_model=RefreshResponse)
async def refresh_store(store_id: int, db: db_dependency):
    """Force-refresh one store's prices. Store failures surface as 503 via main.py's handlers."""
    store = await db.get(Store, store_id)
    if store is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Store not found")
    return RefreshResponse(products_synced=await sync_store(db, store))