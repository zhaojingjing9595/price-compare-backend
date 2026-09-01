from sqlalchemy import (
    Boolean, Column, Integer, String, DECIMAL, ForeignKey,
    UniqueConstraint, DateTime, func,
)
from sqlalchemy.orm import relationship

from db.database import Base


class Store(Base):
    __tablename__ = "store"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True, index=True, nullable=False)
    api_endpoint = Column(String(512), nullable=False)
    # Set once the first successful backfill (cold start) has landed.
    onboarded = Column(Boolean, default=False, nullable=False)
    last_synced_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    products = relationship("Product", back_populates="store")


class Product(Base):
    __tablename__ = "product"

    id = Column(Integer, primary_key=True)
    # MySQL has no trigram index; the nearest option
    # is FULLTEXT WITH PARSER ngram, which needs a server-level ngram_token_size
    # and MATCH ... AGAINST instead of LIKE. Worth it once a scan gets too slow.
    name = Column(String(255), nullable=False)
    external_product_id = Column(String(255))
    # Every write path seeds a price from the store's catalog, so it is never null.
    price = Column(DECIMAL(10, 2), nullable=False)
    last_updated = Column(DateTime, server_default=func.now(), onupdate=func.now())
    store_id = Column(Integer, ForeignKey("store.id"), nullable=False)

    store = relationship("Store", back_populates="products")

    __table_args__ = (
        UniqueConstraint("name", "store_id", name="uq_product_per_store_id"),
    )
