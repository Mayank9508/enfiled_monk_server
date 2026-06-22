from pydantic import BaseModel, EmailStr
from typing import Optional


class AdminCreateUserRequest(BaseModel):
    full_name: str
    email: EmailStr
    phone: str
    password: str
    role: str = "user"
    is_verified: bool = False


class AdminUpdateUserRequest(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None


class AdminResetPasswordRequest(BaseModel):
    new_password: str


class AdminBlockUserRequest(BaseModel):
    is_blocked: bool


class AdminVerifyUserRequest(BaseModel):
    is_verified: bool


class AdminChangeRoleRequest(BaseModel):
    role: str