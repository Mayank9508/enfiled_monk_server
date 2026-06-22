import logging

logger = logging.getLogger(__name__)
from fastapi import APIRouter, Depends
from app.core.database import get_db
from app.schemas.order_schema import PlaceOrderRequest
from app.middleware.auth_middleware import get_current_user
from app.services import order_service

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.post("/")
async def place_order(data: PlaceOrderRequest, current_user: dict = Depends(get_current_user), db=Depends(get_db)):
    user_id = current_user.get("sub")
    return await order_service.place_order(user_id, data, db)


@router.get("/")
async def get_my_orders(current_user: dict = Depends(get_current_user), db=Depends(get_db)):
    user_id = current_user.get("sub")
    return await order_service.get_my_orders(user_id, db)


@router.get("/{order_id}")
async def get_order_by_id(order_id: str, current_user: dict = Depends(get_current_user), db=Depends(get_db)):
    user_id = current_user.get("sub")
    return await order_service.get_order_by_id(order_id, user_id, db)

@router.put("/{order_id}/cancel")
async def cancel_order(order_id: str, current_user: dict = Depends(get_current_user), db=Depends(get_db)):
    user_id = current_user.get("sub")
    return await order_service.cancel_order(order_id, user_id, db)