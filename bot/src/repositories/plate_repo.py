from src.core.db.connection import get_pool


async def get_plate(car_id: str) -> str | None:
    pool = await get_pool()
    row = await pool.fetchrow("SELECT plate FROM car_plates WHERE car_id = $1", car_id)
    return row["plate"] if row else None


async def save_plate(car_id: str, plate: str, reported_by: int) -> None:
    pool = await get_pool()
    await pool.execute(
        "INSERT INTO car_plates (car_id, plate, reported_by) VALUES ($1, $2, $3) "
        "ON CONFLICT (car_id) DO UPDATE SET plate = $2, reported_by = $3, created_at = now()",
        car_id, plate, reported_by)


async def find_plate_by_number(plate: str) -> str | None:
    pool = await get_pool()
    row = await pool.fetchrow("SELECT car_id FROM car_plates WHERE plate = $1", plate)
    return row["car_id"] if row else None
