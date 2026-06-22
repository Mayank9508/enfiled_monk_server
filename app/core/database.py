import asyncpg
from app.core.config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD

pool = None

async def init_db():
    global pool
    pool = await asyncpg.create_pool(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        min_size=2,
        max_size=10
    )

async def get_db():
    async with pool.acquire() as conn:
        yield conn