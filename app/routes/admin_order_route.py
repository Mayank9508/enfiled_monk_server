import logging

logger = logging.getLogger(__name__)
from fastapi import APIRouter, Depends
from typing import Optional
from app.core.database import get_db
from app.schemas.order_schema import UpdateOrderStatusRequest, UpdatePaymentStatusRequest
from app.middleware.auth_middleware import get_current_admin
from app.services import admin_order_service

router = APIRouter(prefix="/admin/orders", tags=["Admin Orders"])


@router.get("/")
async def get_all_orders(
    status: Optional[str] = None,
    payment_status: Optional[str] = None,
    db=Depends(get_db),
    admin=Depends(get_current_admin)
):
    return await admin_order_service.get_all_orders(db, status, payment_status)


@router.get("/{order_id}")
async def get_order_by_id(order_id: str, db=Depends(get_db), admin=Depends(get_current_admin)):
    return await admin_order_service.get_order_by_id(order_id, db)


@router.put("/{order_id}/status")
async def update_order_status(order_id: str, data: UpdateOrderStatusRequest, db=Depends(get_db), admin=Depends(get_current_admin)):
    return await admin_order_service.update_order_status(order_id, data.status, db)


@router.put("/{order_id}/payment-status")
async def update_payment_status(order_id: str, data: UpdatePaymentStatusRequest, db=Depends(get_db), admin=Depends(get_current_admin)):
    return await admin_order_service.update_payment_status(order_id, data.payment_status, db)