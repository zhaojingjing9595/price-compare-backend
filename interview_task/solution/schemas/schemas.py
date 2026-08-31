from pydantic import BaseModel, Field
from decimal import Decimal
from datetime import datetime

#-------Store----------------
class StoreCreate(BaseModel):
    name: str

class StoreResponse(BaseModel):
    id: int
    name: str
    created_at: datetime
    
#---------Product-------------
class ProductCreate(BaseModel):
    name: str
    external_product_id: str
    store_id: int

class ProductResponse(BaseModel):
    id: int
    name: str
    store_id: int
    external_product_id: str
    price: Decimal
    last_updated: datetime
    

class SearchResultItem(BaseModel):
    product_name: str
    store_name: str
    price: Decimal
    last_updated: datetime

    