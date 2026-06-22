from pydantic import BaseModel
from typing import Optional


class AddToCartRequest(BaseModel):
    product_id: str
    quantity: int = 1


class UpdateCartRequest(BaseModel):
    quantity: int