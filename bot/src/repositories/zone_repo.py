from typing import Any

from src.core.db.connection import get_pool


async def get_user_zones(user_id: int) -> list[dict[str, Any]]:
    pool = await get_pool()
    rows = await pool.fetch(
        "SELECT * FROM zones WHERE user_id = $1 ORDER BY zone_id", user_id)
    return [dict(r) for r in rows]


async def get_active_zones(user_id: int) -> list[dict[str, Any]]:
    pool = await get_pool()
    rows = await pool.fetch(
        "SELECT * FROM zones WHERE user_id = $1 AND active = TRUE ORDER BY zone_id",
        user_id)
    return [dict(r) for r in rows]


async def create_zone(user_id: int, lat: float, lon: float, radius: int,
                      name: str = "Зона") -> int:
    pool = await get_pool()
    row = await pool.fetchrow(
        "INSERT INTO zones (user_id, name, lat, lon, radius) "
        "VALUES ($1, $2, $3, $4, $5) RETURNING zone_id",
        user_id, name, lat, lon, radius)
    return row["zone_id"]


async def delete_zone(zone_id: int, user_id: int) -> bool:
    pool = await get_pool()
    row = await pool.fetchrow(
        "DELETE FROM zones WHERE zone_id = $1 AND user_id = $2 RETURNING zone_id",
        zone_id, user_id)
    return row is not None


async def toggle_zone(zone_id: int, user_id: int) -> bool | None:
    pool = await get_pool()
    row = await pool.fetchrow(
        "UPDATE zones SET active = NOT active "
        "WHERE zone_id = $1 AND user_id = $2 RETURNING active",
        zone_id, user_id)
    return row["active"] if row else None


async def rename_zone(zone_id: int, user_id: int, name: str) -> bool:
    pool = await get_pool()
    row = await pool.fetchrow(
        "UPDATE zones SET name = $1 WHERE zone_id = $2 AND user_id = $3 RETURNING zone_id",
        name, zone_id, user_id)
    return row is not None


async def set_zone_schedule(zone_id: int, user_id: int, schedule: str) -> bool:
    pool = await get_pool()
    row = await pool.fetchrow(
        "UPDATE zones SET schedule = $1 WHERE zone_id = $2 AND user_id = $3 RETURNING zone_id",
        schedule, zone_id, user_id)
    return row is not None
