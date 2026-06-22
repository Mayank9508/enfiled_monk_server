import logging

logger = logging.getLogger(__name__)
from fastapi import APIRouter, Depends, HTTPException, Response
from app.core.database import get_db
from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    AuthResponse,
    UserResponse,
    RefreshTokenRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    SendOtpRequest,
    VerifyOtpRequest,
)
from app.middleware.auth_middleware import get_current_user
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register")
async def register(data: RegisterRequest, db=Depends(get_db)):
    return await auth_service.register(data, db)


@router.post("/login", response_model=AuthResponse)
async def login(data: LoginRequest, response: Response, db=Depends(get_db)):
    return await auth_service.login(data, response, db)


@router.post("/refresh")
async def refresh_token(data: RefreshTokenRequest, response: Response, db=Depends(get_db)):
    return await auth_service.refresh_token(data, response, db)


@router.post("/logout")
async def logout(data: RefreshTokenRequest, response: Response, db=Depends(get_db)):
    return await auth_service.logout(data, response, db)


@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user), db=Depends(get_db)):
    return await auth_service.get_me(current_user, db)


@router.post("/forgot-password")
async def forgot_password(data: ForgotPasswordRequest, db=Depends(get_db)):
    return await auth_service.forgot_password(data.email, db)


@router.post("/reset-password")
async def reset_password(data: ResetPasswordRequest, db=Depends(get_db)):
    return await auth_service.reset_password(data.email, data.otp, data.new_password, db)


@router.post("/send-otp")
async def send_otp(data: SendOtpRequest, db=Depends(get_db)):
    return await auth_service.send_otp(data.email, db)


@router.post("/verify-otp")
async def verify_otp(data: VerifyOtpRequest, db=Depends(get_db)):
    return await auth_service.verify_otp(data.email, data.otp, db)