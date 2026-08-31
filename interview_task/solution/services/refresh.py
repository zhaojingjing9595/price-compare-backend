import asyncio
import logging
from datetime import datetime
from decimal import Decimal

from services.config import get_store_base_url
from db.database import SessionLocal
from models.models import Product, Store
from services.store_client import StoreUnavailableError, fetch_products

logger = logging.getLogger(__name__)


async def refresh_store_prices(store_id: int, store_name: str):
    """Refresh every product of one store."""
    base_url = get_store_base_url(store_name)
    if base_url is None:
        logger.warning(
            "No endpoint configured for store '%s' (expected %s_URL); skipping refresh",
            store_name, store_name.upper(),
        )
        return 0

    try:
        catalog = await fetch_products(base_url)
    except StoreUnavailableError as exc:
        logger.warning("Skipping price refresh for store '%s': %s", store_name, exc)
        return 0

    prices = {item["name"]: item["price"] for item in catalog}
    updated = 0

    # Each task gets its own Session: a Session is not safe to share across concurrent tasks.
    with SessionLocal() as db:
        for product in db.query(Product).filter(Product.store_id == store_id):
            new_price = prices.get(product.name)
            if new_price is None:
                logger.warning(
                    "Product '%s' is not listed in store '%s'; leaving its price unchanged",
                    product.name, store_name,
                )
                continue
            product.price = Decimal(str(new_price))
            # Set explicitly: onupdate would not fire when the price is unchanged,
            # leaving last_updated stale even though the price was just confirmed.
            product.last_updated = datetime.now()
            updated += 1
        db.commit()

    logger.info("Refreshed %d listing(s) for store '%s'", updated, store_name)
    return updated


async def refresh_all_prices():
    """Refresh all stores."""
    with SessionLocal() as db:
        stores = [(store.id, store.name) for store in db.query(Store).all()]

    results = await asyncio.gather(*(refresh_store_prices(*store) for store in stores))
    return sum(results)