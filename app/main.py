from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import APP_NAME, DEBUG
from app.core.database import init_db

# ALL Routers import here with specific name
from app.routes.auth import router as auth_router
from app.routes.product_route import router as products_router
from app.routes.user_route import router as user_router
from app.routes.admin_route import router as admin_router
from app.routes.cart_route import router as cart_router
from app.routes.order_route import router as order_router
from app.routes.admin_order_route import router as admin_order_router
from app.routes.bike_route import router as bike_router
from app.routes.booking_route import router as booking_router

import logging

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)

logger = logging.getLogger(__name__)

app = FastAPI(title=APP_NAME, debug=DEBUG)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ALL Routers use here
app.include_router(auth_router)
app.include_router(products_router)
app.include_router(user_router)
app.include_router(admin_router)
app.include_router(cart_router)
app.include_router(order_router)
app.include_router(admin_order_router)
app.include_router(bike_router)
app.include_router(booking_router)


@app.on_event("startup")
async def startup():
    await init_db()
    logger.info("Database connection pool initialized!")


@app.get("/")
def root():
    return {"message": "Enfield Monk API is running!"}
