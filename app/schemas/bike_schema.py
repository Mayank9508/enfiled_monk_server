from pydantic import BaseModel
from typing import Optional, List


class BikeCreate(BaseModel):
    series: str
    variant: str
    engine_cc: int
    title: str
    description: Optional[str] = None
    rent_price_per_day: float
    security_deposit: float
    images: Optional[List[str]] = []
    available_cities: Optional[List[str]] = []
    specifications: Optional[dict] = {}
    status: str = "available"


class BikeUpdate(BaseModel):
    series: Optional[str] = None
    variant: Optional[str] = None
    engine_cc: Optional[int] = None
    title: Optional[str] = None
    description: Optional[str] = None
    rent_price_per_day: Optional[float] = None
    security_deposit: Optional[float] = None
    images: Optional[List[str]] = None
    available_cities: Optional[List[str]] = None
    specifications: Optional[dict] = None
    status: Optional[str] = None