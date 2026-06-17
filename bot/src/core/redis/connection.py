"""Redis connection + ephemeral state (pending plate reports)."""

import redis.asyncio as aioredis
from loguru import logger

from src.settings import get_settings

_redis: aioredis.Redis | None = None

_PENDING_PLATE = "cb:pp:{}"
PENDING_TTL = 300


async def create_redis() -> aioredis.Redis:
    global _redis
    if _redis is not None:
        return _redis
    settings = get_settings()
    _redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    logger.info("Redis connected: {}", settings.REDIS_URL)
    return _redis


async def get_redis() -> aioredis.Redis:
    if _redis is None:
        return await create_redis()
    return _redis


async def close_redis() -> None:
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None
        logger.info("Redis closed")


# ---- pending_plate ----

async def set_pending_plate(user_id: int, car_id: str) -> None:
    r = await get_redis()
    await r.set(_PENDING_PLATE.format(user_id), car_id, ex=PENDING_TTL)


async def get_pending_plate(user_id: int) -> str | None:
    r = await get_redis()
    return await r.get(_PENDING_PLATE.format(user_id))


async def pop_pending_plate(user_id: int) -> str | None:
    r = await get_redis()
    key = _PENDING_PLATE.format(user_id)
    val = await r.get(key)
    if val:
        await r.delete(key)
    return val
