"""Search service: answers GET /products from the local tables only.

No outbound HTTP on the read path — prices are kept current by the onboarding
backfill and the daily refresh, so search stays fast however slow the stores are.
"""
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from models.models import Product


async def search_products(db: AsyncSession, name_contains: str | None = None) -> Sequence[Product]:
    """Listings whose name contains `name_contains`, cheapest first."""
    stmt = (select(Product)
            .options(joinedload(Product.store))
            .order_by(Product.price.asc()))
    if name_contains:
        stmt = stmt.filter(Product.name.contains(name_contains, autoescape=True))
    result = await db.execute(stmt)
    return result.unique().scalars().all()
