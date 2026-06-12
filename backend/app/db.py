import asyncio
import logging
import asyncpg
from app.config import settings

logger = logging.getLogger(__name__)

# asyncpg pools are bound to the event loop that created them. The test suite
# drives the app from two loops (the TestClient lifespan portal and the pytest
# session loop), so pools are kept per-loop. In production there is exactly one
# loop, hence exactly one pool — created once in the FastAPI lifespan.
_pools: dict[int, asyncpg.Pool] = {}


def _loop_id() -> int:
    return id(asyncio.get_running_loop())


async def init_pool() -> None:
    key = _loop_id()
    if key not in _pools:
        _pools[key] = await asyncpg.create_pool(
            settings.DATABASE_URL,
            min_size=2,
            max_size=10,
        )
        logger.info("asyncpg pool created (min=2, max=10)")


async def close_pool() -> None:
    pool = _pools.pop(_loop_id(), None)
    if pool:
        await pool.close()
        logger.info("asyncpg pool closed")


def get_pool() -> asyncpg.Pool:
    pool = _pools.get(_loop_id())
    if pool is None:
        raise RuntimeError("DB pool not initialised — call init_pool() first")
    return pool


async def _acquire_pool() -> asyncpg.Pool:
    key = _loop_id()
    if key not in _pools:
        await init_pool()
    return _pools[key]


async def execute(query: str, *args) -> str:
    pool = await _acquire_pool()
    async with pool.acquire() as conn:
        return await conn.execute(query, *args)


async def fetch(query: str, *args) -> list[asyncpg.Record]:
    pool = await _acquire_pool()
    async with pool.acquire() as conn:
        return await conn.fetch(query, *args)


async def fetchrow(query: str, *args) -> asyncpg.Record | None:
    pool = await _acquire_pool()
    async with pool.acquire() as conn:
        return await conn.fetchrow(query, *args)


async def fetchval(query: str, *args):
    pool = await _acquire_pool()
    async with pool.acquire() as conn:
        return await conn.fetchval(query, *args)
