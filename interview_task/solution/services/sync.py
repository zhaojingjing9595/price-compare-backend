"""Store synchronisation: pulling a store's catalog into our local tables.

Two callers share the same core (`sync_store`):

* `cold_start`         — the onboarding backfill, fired once when a store is registered.
* `refresh_all_stores` — the daily job, run by the scheduler for every onboarded store.
"""

import asyncio
import logging
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import AsyncSessionLocal
from models.models import Product, Store
from services.store_client import (
    StoreDataError,
    StoreUnavailableError,
    fetch_products,
)

logger = logging.getLogger(__name__)

# Stores are refreshed concurrently, but not unboundedly: each task holds its own
# DB session, so the cap also caps connection-pool usage.
MAX_CONCURRENT_STORE_SYNCS = 5


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def parse_listing(item: dict) -> tuple[str, str | None, Decimal]:
    """Validate one raw catalog entry. Raises StoreDataError if it is unusable."""
    try:
        name = item["name"]
        price = Decimal(str(item["price"]))
    except (TypeError, KeyError, InvalidOperation) as exc:
        raise StoreDataError(f"malformed listing: {item!r}") from exc
    return name, item.get("external_product_id"), price


async def upsert_products(db: AsyncSession, store: Store, items: list[dict]) -> int:
    """Insert or update a store's listings. Malformed entries are skipped, not fatal."""
    stmt = select(Product).filter_by(store_id=store.id)
    result = await db.execute(stmt)
    existing = {p.name: p for p in result.scalars()}
    count = 0

    for item in items:
        try:
            name, external_id, price = parse_listing(item)
        except StoreDataError as exc:
            logger.warning("[%s] skipping listing: %s", store.name, exc)
            continue

        product = existing.get(name)
        if product:
            product.external_product_id = external_id
            product.price = price
            product.last_updated = _now()
        else:
            db.add(
                Product(
                    name=name,
                    store_id=store.id,
                    external_product_id=external_id,
                    price=price,
                    last_updated=_now(),
                )
            )
        count += 1

    await db.commit()
    return count


async def sync_store(db: AsyncSession, store: Store) -> int:
    """Pull a store's full catalog and write it locally. Returns the number of listings."""
    items = await fetch_products(store.api_endpoint)
    count = await upsert_products(db, store, items)

    store.onboarded = True
    store.last_synced_at = _now()
    await db.commit()
    return count


async def cold_start(store_id: int) -> None:
    """Onboarding backfill. Runs in the background, so it must never raise."""
    async with AsyncSessionLocal() as db:
        store = await db.get(Store, store_id)
        if store is None:
            logger.error("[cold start] store %s no longer exists", store_id)
            return
        try:
            count = await sync_store(db, store)
            logger.info("[cold start] %s: %d products backfilled", store.name, count)
        except (StoreUnavailableError, StoreDataError) as exc:
            # Left un-onboarded on purpose: the store is retried by the daily job.
            logger.warning("[cold start] %s failed, will retry on refresh: %s", store.name, exc)
        except Exception:
            logger.exception("[cold start] %s failed unexpectedly", store.name)


async def _refresh_one(store_id: int, semaphore: asyncio.Semaphore) -> int:
    """Refresh a single store in its own Session — a Session is not concurrency-safe."""
    async with semaphore:
        async with AsyncSessionLocal() as db:
            store = await db.get(Store, store_id)
            if store is None:
                return 0
            try:
                count = await sync_store(db, store)
                logger.info("[refresh] %s: %d products synced", store.name, count)
                return count
            except (StoreUnavailableError, StoreDataError) as exc:
                logger.warning("[refresh] %s failed: %s", store.name, exc)
            except Exception:
                logger.exception("[refresh] %s failed unexpectedly", store.name)
            return 0


async def refresh_all_stores() -> int:
    """The daily job. Refreshes every onboarded store concurrently; one bad store
    never aborts the cycle. Returns the total number of listings synced."""
    async with AsyncSessionLocal() as db:
        stmt = select(Store.id).filter_by(onboarded=True)
        result = await db.execute(stmt)
        store_ids = result.scalars().all()

    if not store_ids:
        logger.info("[refresh] no onboarded stores")
        return 0

    semaphore = asyncio.Semaphore(MAX_CONCURRENT_STORE_SYNCS)
    counts = await asyncio.gather(*(_refresh_one(sid, semaphore) for sid in store_ids))
    total = sum(counts)
    logger.info("[refresh] done: %d listing(s) across %d store(s)", total, len(store_ids))
    return total
