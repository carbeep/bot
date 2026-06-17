"""Delimobil public API client."""

from __future__ import annotations

from typing import Any

import aiohttp
from loguru import logger

from src.services.geo import haversine

API_URL = "https://api.delimobil.ru/api/cars"
HEADERS = {
    "Accept": "application/json",
    "Origin": "https://delimobil.ru",
    "Referer": "https://delimobil.ru/",
}


async def fetch_cars(region_id: int) -> list[dict[str, Any]]:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                API_URL, params={"regionId": region_id},
                headers=HEADERS, timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status != 200:
                    logger.warning("Delimobil API %d", resp.status)
                    return []
                data = await resp.json()
    except Exception as exc:
        logger.error("Delimobil API error: %s", exc)
        return []

    cars: list[dict[str, Any]] = []
    for feat in data.get("geojson", {}).get("features", []):
        car_id = str(feat.get("id", ""))
        coords = feat.get("geometry", {}).get("coordinates", [])
        props = feat.get("properties", {})
        if len(coords) >= 2 and car_id:
            cars.append({
                "id": car_id,
                "lon": float(coords[0]),
                "lat": float(coords[1]),
                "model": props.get("model", "Авто").strip(),
            })
    return cars


def find_cars_near(
    cars: list[dict[str, Any]], lat: float, lon: float, radius: int,
) -> list[dict[str, Any]]:
    result = []
    for car in cars:
        dist = haversine(lat, lon, car["lat"], car["lon"])
        if dist <= radius:
            result.append({**car, "distance": dist})
    result.sort(key=lambda c: c["distance"])
    return result


def model_title(model: str) -> str:
    return " ".join(w.capitalize() for w in model.split())


def matches_filter(model: str, filter_str: str) -> bool:
    if not filter_str:
        return True
    keywords = [kw.strip().lower() for kw in filter_str.split(",") if kw.strip()]
    return not keywords or any(kw in model.lower() for kw in keywords)
