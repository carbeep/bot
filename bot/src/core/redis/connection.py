import redis.asyncio as aioredis
from loguru import logger

from src.settings import get_settings

_redis: aioredis.Redis | None = None

_PENDING_PLATE = "cb:pp:{}"
_NEXT_ZONE_NAME = "cb:zn:{}"
_NOTIFIED = "cb:nf:{}:{}"

PENDING_TTL = 300
ZONE_NAME_TTL = 300


def _notified_ttl() -> int:
    return get_settings().NOTIFY_TTL_MINUTES * 60


async def create_redis() -> aioredis.Redis:
    global _redis
    if _redis is not None:
        return _redis
    settings = get_settings()
    _redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    logger.info("Redis connected: %s", settings.REDIS_URL)
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


# ---- next_zone_name ----

async def set_next_zone_name(user_id: int, name: str) -> None:
    r = await get_redis()
    await r.set(_NEXT_ZONE_NAME.format(user_id), name, ex=ZONE_NAME_TTL)


async def pop_next_zone_name(user_id: int) -> str | None:
    r = await get_redis()
    key = _NEXT_ZONE_NAME.format(user_id)
    val = await r.get(key)
    if val:
        await r.delete(key)
    return val


# ---- notified dedup ----

async def was_notified(user_id: int, car_id: str) -> bool:
    r = await get_redis()
    return await r.exists(_NOTIFIED.format(user_id, car_id)) > 0


async def mark_notified(user_id: int, car_id: str) -> None:
    r = await get_redis()
    await r.set(_NOTIFIED.format(user_id, car_id), "1", ex=_notified_ttl())


async def cleanup_notified() -> None:
    pass  # Redis TTL handles expiry
