"""Search service: answers GET /products from the local tables only.

No outbound HTTP on the read path — prices are kept current by the onboarding
backfill and the daily refresh, so search stays fast however slow the stores are.
"""

from sqlalchemy.orm import Session, joinedload

from models.models import Product


def search_products(db: Session, name_contains: str) -> list[Product]:
    """Listings whose name contains `name_contains`, cheapest first."""
    return (
        db.query(Product)
        .options(joinedload(Product.store))
        .filter(Product.name.contains(name_contains, autoescape=True))
        .filter(Product.price.isnot(None))
        .order_by(Product.price.asc())
        .all()
    )
