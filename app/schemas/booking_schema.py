from pydantic import BaseModel
from typing import Optional
from datetime import date


class CreateBookingRequest(BaseModel):
    bike_id: str
    city: str
    start_date: date
    end_date: date
    pickup_location: Optional[str] = None
    drop_location: Optional[str] = None
    notes: Optional[str] = None