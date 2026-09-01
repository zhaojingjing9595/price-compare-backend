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
    # Full URL of the store's GET products endpoint. Single source of truth:
    # onboarding, the daily refresh and product registration all read it from here.
    api_endpoint = Column(String(512), nullable=False)
    # Set once the first successful backfill (cold start) has landed.
    onboarded = Column(Boolean, default=False, nullable=False)
    last_synced_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    products = relationship("Product", back_populates="store")


class Product(Base):
    __tablename__ = "product"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), index=True, nullable=False)
    external_product_id = Column(String(255))
    price = Column(DECIMAL(10, 2))
    last_updated = Column(DateTime, server_default=func.now(), onupdate=func.now())
    store_id = Column(Integer, ForeignKey("store.id"), nullable=False)

    store = relationship("Store", back_populates="products")

    __table_args__ = (
        UniqueConstraint("name", "store_id", name="uq_product_per_store_id"),
    )
