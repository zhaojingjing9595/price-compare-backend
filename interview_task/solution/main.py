"""Price comparison API.

Three services make up the backend:

1. Onboarding  — POST /stores registers a store and backfills its catalog
                 in the background (services/sync.py: cold_start).
2. Scheduler   — refreshes every onboarded store once a day
                 (services/sync.py: refresh_all_stores), wired up below.
3. Search      — GET /products answers from the local tables (services/search.py).
"""

import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI

from db.database import Base, engine
from errors import register_error_handlers
from routers.products import router as product_router
from routers.stores import router as store_router
from services.sync import refresh_all_stores

logging.basicConfig(level=logging.INFO)

REFRESH_INTERVAL_HOURS = 24

@asynccontextmanager
async def lifespan(_app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Stores publish prices once a day. The first sync of a store happens at
    # onboarding, so this job only keeps already-onboarded stores current.
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        refresh_all_stores,
        "interval",
        hours=REFRESH_INTERVAL_HOURS,
        id="refresh_all_stores",
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    try:
        yield
    finally:
        scheduler.shutdown(wait=False)


app = FastAPI(title="Price Comparison API", lifespan=lifespan)

app.include_router(store_router)
app.include_router(product_router)
register_error_handlers(app)


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=9991)
