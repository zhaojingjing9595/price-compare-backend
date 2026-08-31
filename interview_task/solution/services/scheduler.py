import asyncio
import logging

from services.refresh import refresh_all_prices

logger = logging.getLogger(__name__)

REFRESH_INTERVAL_SECONDS = 24 * 60 * 60


async def _refresh_loop():
    """Refresh immediately on startup, then once a day — stores update prices daily."""
    while True:
        try:
            await refresh_all_prices()
        except Exception:
            logger.exception("Scheduled price refresh failed; will retry next cycle")
        await asyncio.sleep(REFRESH_INTERVAL_SECONDS)


def start_scheduler():
    return asyncio.create_task(_refresh_loop())