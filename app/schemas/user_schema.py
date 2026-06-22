from pydantic import BaseModel, EmailStr
from typing import Optional, List


class AddressSchema(BaseModel):
    label: Optional[str] = None   # jese - home ya Office , ghar
    full_address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    is_default: bool = False


class UpdateProfileRequest(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None


class AddAddressRequest(BaseModel):
    address: AddressSchema


class UpdateAddressRequest(BaseModel):
    address: AddressSchema


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str

