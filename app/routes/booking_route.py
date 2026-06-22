import logging

logger = logging.getLogger(__name__)
from fastapi import APIRouter, Depends
from app.core.database import get_db
from app.schemas.booking_schema import CreateBookingRequest
from app.middleware.auth_middleware import get_current_user
from app.services import booking_service

router = APIRouter(prefix="/bookings", tags=["Bookings"])


@router.get("/check-availability/{bike_id}")
async def check_availability(bike_id: str, db=Depends(get_db)):
    return await booking_service.check_availability(bike_id, db)


@router.post("/")
async def create_booking(data: CreateBookingRequest, current_user: dict = Depends(get_current_user), db=Depends(get_db)):
    user_id = current_user.get("sub")
    return await booking_service.create_booking(user_id, data, db)


@router.get("/")
async def get_my_bookings(current_user: dict = Depends(get_current_user), db=Depends(get_db)):
    user_id = current_user.get("sub")
    return await booking_service.get_my_bookings(user_id, db)


@router.put("/{booking_id}/cancel")
async def cancel_booking(booking_id: str, current_user: dict = Depends(get_current_user), db=Depends(get_db)):
    user_id = current_user.get("sub")
    return await booking_service.cancel_booking(booking_id, user_id, db)