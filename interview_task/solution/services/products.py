from sqlalchemy.orm import Session, joinedload

from models.models import Product


def search(db: Session, name_contains: str):
    """Local-only search. Never touches a store: prices are kept current by the refresh job."""
    return (
        db.query(Product)
        .options(joinedload(Product.store))
        .filter(Product.name.contains(name_contains, autoescape=True))
        .filter(Product.price.isnot(None))
        .order_by(Product.price.asc())
        .all()
    )