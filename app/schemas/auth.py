from pydantic import BaseModel, EmailStr


class RegisterRequest(BaseModel):
    full_name: str
    email: EmailStr
    phone: str
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: str
    full_name: str
    email: str
    role: str


class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


class RefreshTokenRequest(BaseModel):
    refresh_token: str


# Forget pass and reset passowrd Schemas
class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    otp: str
    new_password: str

# OPT verifiaction when user register 1s tiem 
class SendOtpRequest(BaseModel):
    email: EmailStr

# OPT verifiaction with email when user forget password   
class VerifyOtpRequest(BaseModel):
    email: EmailStr
    otp: str
