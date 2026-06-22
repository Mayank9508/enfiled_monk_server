import logging

logger = logging.getLogger(__name__)
from fastapi import APIRouter, Depends
from typing import Optional
from app.core.database import get_db
from app.schemas.bike_schema import BikeCreate, BikeUpdate
from app.middleware.auth_middleware import get_current_admin
from app.services import bike_service

router = APIRouter(prefix="/bikes", tags=["Bikes"])


@router.get("/")
async def get_all_bikes(
    series: Optional[str] = None,
    city: Optional[str] = None,
    status: Optional[str] = "available",
    db=Depends(get_db)
):
    return await bike_service.get_all_bikes(db, series, city, status)


@router.get("/{bike_id}")
async def get_bike_by_id(bike_id: str, db=Depends(get_db)):
    return await bike_service.get_bike_by_id(bike_id, db)


@router.post("/")
async def create_bike(data: BikeCreate, db=Depends(get_db), admin=Depends(get_current_admin)):
    return await bike_service.create_bike(data, db)


@router.put("/{bike_id}")
async def update_bike(bike_id: str, data: BikeUpdate, db=Depends(get_db), admin=Depends(get_current_admin)):
    return await bike_service.update_bike(bike_id, data, db)


@router.delete("/{bike_id}")
async def delete_bike(bike_id: str, db=Depends(get_db), admin=Depends(get_current_admin)):
    return await bike_service.delete_bike(bike_id, db)