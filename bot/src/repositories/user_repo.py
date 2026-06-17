from typing import Any

from src.core.db.connection import get_pool


async def ensure_user(user_id: int) -> None:
    pool = await get_pool()
    await pool.execute(
        "INSERT INTO users (user_id) VALUES ($1) ON CONFLICT DO NOTHING", user_id)


async def get_user(user_id: int) -> dict[str, Any]:
    pool = await get_pool()
    row = await pool.fetchrow("SELECT * FROM users WHERE user_id = $1", user_id)
    return dict(row) if row else {}


async def update_user(user_id: int, **kwargs: Any) -> None:
    pool = await get_pool()
    sets = ", ".join(f"{k} = ${i+1}" for i, k in enumerate(kwargs))
    vals = list(kwargs.values()) + [user_id]
    await pool.execute(
        f"UPDATE users SET {sets} WHERE user_id = ${len(kwargs)+1}", *vals)


async def get_all_users() -> list[dict[str, Any]]:
    pool = await get_pool()
    rows = await pool.fetch("SELECT * FROM users")
    return [dict(r) for r in rows]
