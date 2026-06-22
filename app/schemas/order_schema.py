from pydantic import BaseModel
from typing import Optional


class AddressSchema(BaseModel):
    label: Optional[str] = None
    full_address: str
    city: str
    state: str
    pincode: str


class PlaceOrderRequest(BaseModel):
    address_index: Optional[int] = None     # saved address ka index
    new_address: Optional[AddressSchema] = None  # naya address (agar saved nahi use karna)
    coupon_code: Optional[str] = None
    payment_method: str = "cod"             # abhi sirf "cod"


class UpdateOrderStatusRequest(BaseModel):
    status: str


class UpdatePaymentStatusRequest(BaseModel):
    payment_status: str