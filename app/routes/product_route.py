import logging

logger = logging.getLogger(__name__)
from fastapi import APIRouter, Depends
from typing import Optional
from app.core.database import get_db
from app.schemas.product_schema import ProductCreate, ProductUpdate
from app.middleware.auth_middleware import get_current_admin
from app.services import product_service

router = APIRouter(prefix="/products", tags=["Products"])


# Public routes — koi bhi dekh sakta hai
@router.get("/")
async def get_all_products(
    category: Optional[str] = None,
    sub_category: Optional[str] = None,
    search: Optional[str] = None,
    db=Depends(get_db),
):
    return await product_service.get_all_products(db, category, sub_category, search)


@router.get("/{product_id}")
async def get_product(product_id: str, db=Depends(get_db)):
    return await product_service.get_product_by_id(product_id, db)


# Admin routes — sirf admin access kar sakta hai
@router.post("/")
async def create_product(
    data: ProductCreate, db=Depends(get_db), admin=Depends(get_current_admin)
):
    return await product_service.create_product(data, db)


@router.put("/{product_id}")
async def update_product(
    product_id: str,
    data: ProductUpdate,
    db=Depends(get_db),
    admin=Depends(get_current_admin),
):
    return await product_service.update_product(product_id, data, db)


@router.delete("/{product_id}")
async def delete_product(
    product_id: str, db=Depends(get_db), admin=Depends(get_current_admin)
):
    return await product_service.delete_product(product_id, db)