import logging

logger = logging.getLogger(__name__)
from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from app.core.database import get_db
from app.schemas.cart_schema import AddToCartRequest, UpdateCartRequest
from app.middleware.auth_middleware import get_current_user
from app.services import cart_service
from app.utils.jwt import verify_token

router = APIRouter(prefix="/cart", tags=["Cart"])

security = HTTPBearer(auto_error=False)


async def get_user_or_session(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    x_session_id: Optional[str] = Header(None)
):
    user_id = None
    session_id = None

    if credentials:
        token = credentials.credentials
        payload = verify_token(token)
        if payload:
            user_id = payload.get("sub")

    if not user_id:
        if not x_session_id:
            raise HTTPException(status_code=400, detail="Session ID required for guest cart")
        session_id = x_session_id

    return user_id, session_id


@router.get("/")
async def get_cart(identity=Depends(get_user_or_session), db=Depends(get_db)):
    user_id, session_id = identity
    return await cart_service.get_cart(user_id, session_id, db)


@router.post("/items")
async def add_to_cart(data: AddToCartRequest, identity=Depends(get_user_or_session), db=Depends(get_db)):
    user_id, session_id = identity
    return await cart_service.add_to_cart(user_id, session_id, data, db)


@router.put("/items/{cart_item_id}")
async def update_cart_item(cart_item_id: str, data: UpdateCartRequest, identity=Depends(get_user_or_session), db=Depends(get_db)):
    user_id, session_id = identity
    return await cart_service.update_cart_item(cart_item_id, user_id, session_id, data, db)


@router.delete("/items/{cart_item_id}")
async def remove_cart_item(cart_item_id: str, identity=Depends(get_user_or_session), db=Depends(get_db)):
    user_id, session_id = identity
    return await cart_service.remove_cart_item(cart_item_id, user_id, session_id, db)


@router.post("/merge")
async def merge_cart(x_session_id: str = Header(...), current_user: dict = Depends(get_current_user), db=Depends(get_db)):
    user_id = current_user.get("sub")
    return await cart_service.merge_cart(user_id, x_session_id, db)


@router.delete("/clear")
async def clear_cart(identity=Depends(get_user_or_session), db=Depends(get_db)):
    user_id, session_id = identity
    return await cart_service.clear_cart(user_id, session_id, db)