import logging

logger = logging.getLogger(__name__)
from fastapi import APIRouter, Depends
from app.core.database import get_db
from app.schemas.user_schema import (
    UpdateProfileRequest,
    AddAddressRequest,
    UpdateAddressRequest,
    ChangePasswordRequest,
)
from app.middleware.auth_middleware import get_current_user, get_current_admin
from app.services import user_service

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me")
async def get_profile(current_user: dict = Depends(get_current_user), db=Depends(get_db)):
    return await user_service.get_profile(current_user, db)


@router.put("/me")
async def update_profile(data: UpdateProfileRequest, current_user: dict = Depends(get_current_user), db = Depends(get_db)):
    return await user_service.update_profile(current_user, data, db)


@router.post("/me/addresses")
async def add_address(data: AddAddressRequest, current_user: dict = Depends(get_current_user), db=Depends(get_db)):
    return await user_service.add_address(current_user, data, db)


@router.put("/me/addresses/{index}")
async def update_address(index: int, data: UpdateAddressRequest, current_user: dict = Depends(get_current_user), db=Depends(get_db)):
    return await user_service.update_address(current_user, index, data, db)


@router.delete("/me/addresses/{index}")
async def delete_address(index: int, current_user: dict = Depends(get_current_user), db=Depends(get_db)):
    return await user_service.delete_address(current_user, index, db)


@router.put("/me/change-password")
async def change_password(data: ChangePasswordRequest, current_user: dict = Depends(get_current_user), db=Depends(get_db)):
    return await user_service.change_password(current_user, data, db)
