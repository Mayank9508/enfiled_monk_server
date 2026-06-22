from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID
from datetime import datetime

class ProductCreate(BaseModel):
    category: str
    sub_category: Optional[str] = None
    child_category: Optional[str] = None
    name: str
    slug: str
    description: Optional[str] = None
    price: float
    sale_price: Optional[float] = None
    stock: int = 0
    images: Optional[List[str]] = []
    compatible_bikes: Optional[List[dict]] = []
    is_active: bool = True

class ProductUpdate(BaseModel):
    category: Optional[str] = None
    sub_category: Optional[str] = None
    child_category: Optional[str] = None
    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    sale_price: Optional[float] = None
    stock: Optional[int] = None
    images: Optional[List[str]] = None
    compatible_bikes: Optional[List[dict]] = None
    is_active: Optional[bool] = None