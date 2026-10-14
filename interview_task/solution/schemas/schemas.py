from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, HttpUrl


# ---------- Store ----------
class StoreCreate(BaseModel):
    name: str
    api_endpoint: HttpUrl  # full URL of the store's GET products endpoint


class StoreResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    api_endpoint: str
    onboarded: bool
    last_synced_at: datetime | None
    created_at: datetime


class StoreOnboardResponse(BaseModel):
    store_id: int
    name: str
    status: str
    message: str


# ---------- Product ----------
class ProductCreate(BaseModel):
    name: str
    external_product_id: str
    store_id: int


class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    store_id: int
    external_product_id: str | None
    price: Decimal
    last_updated: datetime


class SearchResultItem(BaseModel):
    product_name: str
    store_name: str
    price: Decimal
    last_updated: datetime

class RefreshResponse(BaseModel):
    products_synced: int