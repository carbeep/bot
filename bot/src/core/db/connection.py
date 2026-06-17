from pathlib import Path

import asyncpg
from loguru import logger

from src.settings import get_settings

_pool: asyncpg.Pool | None = None


async def create_pool() -> asyncpg.Pool:
    global _pool
    if _pool is not None:
        return _pool

    settings = get_settings()
    _pool = await asyncpg.create_pool(
        settings.database_url,
        min_size=settings.POSTGRES_MIN_CONNECTIONS,
        max_size=settings.POSTGRES_MAX_CONNECTIONS,
    )
    await _run_migrations(_pool)
    logger.info("PostgreSQL pool created: %s:%d/%s",
                settings.POSTGRES_HOST, settings.POSTGRES_PORT, settings.POSTGRES_DB)
    return _pool


async def get_pool() -> asyncpg.Pool:
    if _pool is None:
        return await create_pool()
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
        logger.info("PostgreSQL pool closed")


async def _run_migrations(pool: asyncpg.Pool) -> None:
    migrations_dir = Path(__file__).parent.parent.parent.parent / "migrations"
    for sql_file in sorted(migrations_dir.glob("*.sql")):
        sql = sql_file.read_text()
        await pool.execute(sql)
        logger.info("Migration applied: %s", sql_file.name)
