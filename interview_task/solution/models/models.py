from sqlalchemy import Column, Integer, Index, String, DECIMAL, ForeignKey, UniqueConstraint, DateTime, func
from db.database import Base
from sqlalchemy.orm import relationship

class Store(Base):
    __tablename__ = "store"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True, index=True)
    created_at = Column(DateTime, server_default=func.now())
    
    products = relationship("Product", back_populates="store")
    
class Product(Base):
    __tablename__ = "product"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), index=True)
    external_product_id = Column(String(255))
    price = Column(DECIMAL(10, 2))
    last_updated = Column(DateTime, server_default=func.now(), onupdate=func.now())
    store_id = Column(Integer, ForeignKey("store.id"), nullable=False)
    
    store = relationship("Store", back_populates="products")
    
    __table_args__ = (
        UniqueConstraint("name", "store_id", name="uq_product_per_store_id"),
    )