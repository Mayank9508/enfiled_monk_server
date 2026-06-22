import logging

logger = logging.getLogger(__name__)
from fastapi import APIRouter, Depends
from app.core.database import get_db
from app.schemas.admin_schema import AdminCreateUserRequest, AdminUpdateUserRequest, AdminResetPasswordRequest, AdminBlockUserRequest, AdminVerifyUserRequest, AdminChangeRoleRequest
from app.middleware.auth_middleware import get_current_admin
from app.services import admin_service

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/users")
async def get_all_users(db=Depends(get_db), admin=Depends(get_current_admin)):
    return await admin_service.get_all_users(db)


@router.get("/users/{user_id}")
async def get_user_by_id(user_id: str, db=Depends(get_db), admin=Depends(get_current_admin)):
    return await admin_service.get_user_by_id(user_id, db)


@router.post("/users")
async def create_user(data: AdminCreateUserRequest, db=Depends(get_db), admin=Depends(get_current_admin)):
    return await admin_service.create_user(data, db)


@router.put("/users/{user_id}")
async def update_user(user_id: str, data: AdminUpdateUserRequest, db=Depends(get_db), admin=Depends(get_current_admin)):
    return await admin_service.update_user(user_id, data, db)

@router.delete("/users/{user_id}")
async def delete_user(user_id: str, db=Depends(get_db), admin=Depends(get_current_admin)):
    return await admin_service.delete_user(user_id, db)


@router.put("/users/{user_id}/reset-password")
async def reset_user_password(user_id: str, data: AdminResetPasswordRequest, db=Depends(get_db), admin=Depends(get_current_admin)):
    return await admin_service.reset_user_password(user_id, data, db)

@router.put("/users/{user_id}/block-unblock")
async def block_unblock_user(user_id: str, data: AdminBlockUserRequest, db=Depends(get_db), admin=Depends(get_current_admin)):
    return await admin_service.block_user(user_id, data, db)


@router.put("/users/{user_id}/verify")
async def verify_user(user_id: str, data: AdminVerifyUserRequest, db=Depends(get_db), admin=Depends(get_current_admin)):
    return await admin_service.verify_user(user_id, data, db)


@router.put("/users/{user_id}/role")
async def change_role(user_id: str, data: AdminChangeRoleRequest, db=Depends(get_db), admin=Depends(get_current_admin)):
    return await admin_service.change_role(user_id, data, db)