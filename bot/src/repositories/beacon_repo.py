from typing import Any

from src.core.db.connection import get_pool


async def create_beacon(user_id: int, chat_id: int, lat: float, lon: float,
                        radius: int = 1000, model_filter: str = "") -> dict[str, Any]:
    pool = await get_pool()
    row = await pool.fetchrow(
        "INSERT INTO beacons (user_id, chat_id, lat, lon, radius, model_filter) "
        "VALUES ($1, $2, $3, $4, $5, $6) RETURNING *",
        user_id, chat_id, lat, lon, radius, model_filter)
    return dict(row)


async def get_active_beacons() -> list[dict[str, Any]]:
    pool = await get_pool()
    rows = await pool.fetch(
        "SELECT b.*, u.region_id FROM beacons b "
        "JOIN users u ON u.user_id = b.user_id "
        "WHERE b.state != 'stopped' AND b.expires_at > now() "
        "ORDER BY b.beacon_id")
    return [dict(r) for r in rows]


async def get_user_beacon(user_id: int) -> dict[str, Any] | None:
    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT * FROM beacons "
        "WHERE user_id = $1 AND state != 'stopped' AND expires_at > now() "
        "ORDER BY beacon_id DESC LIMIT 1", user_id)
    return dict(row) if row else None


async def update_beacon(beacon_id: int, expected_state: str | None = None,
                        **kwargs: Any) -> dict[str, Any] | None:
    pool = await get_pool()
    kwargs["updated_at"] = "now()"
    raw_keys = {"updated_at"}  # SQL expressions, not parameterized

    parts, vals, idx = [], [], 1
    for k, v in kwargs.items():
        if k in raw_keys:
            parts.append(f"{k} = {v}")
        else:
            parts.append(f"{k} = ${idx}")
            vals.append(v)
            idx += 1

    where = f"beacon_id = ${idx}"
    vals.append(beacon_id)
    idx += 1

    if expected_state:
        where += f" AND state = ${idx}"
        vals.append(expected_state)

    row = await pool.fetchrow(
        f"UPDATE beacons SET {', '.join(parts)} WHERE {where} RETURNING *", *vals)
    return dict(row) if row else None


async def set_message_id(beacon_id: int, message_id: int) -> None:
    pool = await get_pool()
    await pool.execute(
        "UPDATE beacons SET message_id = $1 WHERE beacon_id = $2",
        message_id, beacon_id)


async def add_skipped_car(beacon_id: int, car_id: str) -> None:
    pool = await get_pool()
    await pool.execute(
        "UPDATE beacons SET skipped_cars = "
        "CASE WHEN skipped_cars = '' THEN $1 ELSE skipped_cars || ',' || $1 END, "
        "updated_at = now() "
        "WHERE beacon_id = $2", car_id, beacon_id)


async def stop_beacon(beacon_id: int) -> dict[str, Any] | None:
    pool = await get_pool()
    row = await pool.fetchrow(
        "UPDATE beacons SET state = 'stopped', updated_at = now() "
        "WHERE beacon_id = $1 RETURNING *", beacon_id)
    return dict(row) if row else None


async def stop_user_beacons(user_id: int) -> list[dict[str, Any]]:
    pool = await get_pool()
    rows = await pool.fetch(
        "UPDATE beacons SET state = 'stopped', updated_at = now() "
        "WHERE user_id = $1 AND state != 'stopped' RETURNING *", user_id)
    return [dict(r) for r in rows]


async def expire_beacons() -> list[dict[str, Any]]:
    pool = await get_pool()
    rows = await pool.fetch(
        "UPDATE beacons SET state = 'stopped', updated_at = now() "
        "WHERE state != 'stopped' AND expires_at <= now() RETURNING *")
    return [dict(r) for r in rows]
