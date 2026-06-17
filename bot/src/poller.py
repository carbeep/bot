"""Beacon-driven polling loop with state machine."""

import asyncio
from typing import Any

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from loguru import logger

from src.repositories.beacon_repo import expire_beacons, get_active_beacons, update_beacon
from src.repositories.plate_repo import get_plate
from src.services.beacon_messages import (
    render_found, render_gone, render_monitoring, render_searching, render_stopped,
)
from src.services.delimobil import fetch_cars, find_cars_near, matches_filter
from src.services.geo import haversine
from src.settings import get_settings


async def poll_loop(bot: Bot) -> None:
    s = get_settings()
    logger.info("Poll loop started (interval={}s)", s.POLL_INTERVAL)
    while True:
        try:
            await _tick(bot)
        except Exception:
            logger.exception("Poll tick error")
        await asyncio.sleep(s.POLL_INTERVAL)


async def _tick(bot: Bot) -> None:
    # Expire old beacons
    for b in await expire_beacons():
        text, kb = render_stopped(b)
        await _edit(bot, b, text, kb)

    beacons = await get_active_beacons()
    if not beacons:
        return

    # Group by region to minimize API calls
    by_region: dict[int, list[dict[str, Any]]] = {}
    for b in beacons:
        by_region.setdefault(b["region_id"], []).append(b)

    for region_id, region_beacons in by_region.items():
        cars = await fetch_cars(region_id)
        if not cars:
            continue
        for beacon in region_beacons:
            await _process_beacon(bot, beacon, cars)


async def _process_beacon(bot: Bot, beacon: dict[str, Any], cars: list[dict[str, Any]]) -> None:
    state = beacon["state"]
    bid = beacon["beacon_id"]
    skipped = set(beacon.get("skipped_cars", "").split(",")) - {""}
    filt = beacon.get("model_filter") or ""

    if state == "searching":
        await _handle_searching(bot, beacon, cars, skipped, filt)
    elif state == "found":
        await _handle_found(bot, beacon, cars)
    elif state == "monitoring":
        await _handle_monitoring(bot, beacon, cars)
    elif state == "gone":
        await _handle_gone(bot, beacon, cars, skipped, filt)


async def _handle_searching(bot: Bot, beacon: dict, cars: list, skipped: set, filt: str) -> None:
    nearby = find_cars_near(cars, beacon["lat"], beacon["lon"], beacon["radius"])
    if filt:
        nearby = [c for c in nearby if matches_filter(c["model"], filt)]
    nearby = [c for c in nearby if c["id"] not in skipped]

    if nearby:
        car = nearby[0]
        plate = await get_plate(car["id"])
        updated = await update_beacon(
            beacon["beacon_id"],
            expected_state="searching",
            state="found",
            current_car_id=car["id"],
            current_car_model=car["model"],
            current_car_distance=car["distance"],
            current_car_lat=car["lat"],
            current_car_lon=car["lon"],
            cars_found_count=beacon["cars_found_count"] + 1,
        )
        if updated:
            text, kb = render_found(updated, plate)
            await _edit(bot, updated, text, kb)
    else:
        text, kb = render_searching(beacon)
        await _edit(bot, beacon, text, kb)


async def _handle_found(bot: Bot, beacon: dict, cars: list) -> None:
    # Check if car is still available
    car_id = beacon.get("current_car_id")
    still_here = _car_still_near(beacon, cars, car_id)

    if still_here:
        plate = await get_plate(car_id)
        updated = await update_beacon(
            beacon["beacon_id"], expected_state="found", state="monitoring")
        if updated:
            text, kb = render_monitoring(updated, plate)
            await _edit(bot, updated, text, kb)
    else:
        updated = await update_beacon(
            beacon["beacon_id"], expected_state="found", state="gone")
        if updated:
            text, kb = render_gone(updated)
            await _edit(bot, updated, text, kb)


async def _handle_monitoring(bot: Bot, beacon: dict, cars: list) -> None:
    car_id = beacon.get("current_car_id")
    still_here = _car_still_near(beacon, cars, car_id)

    if still_here:
        # Update distance
        car = next((c for c in cars if str(c.get("id")) == str(car_id)), None)
        dist = haversine(beacon["lat"], beacon["lon"], car["lat"], car["lon"]) if car else None
        plate = await get_plate(car_id)
        updated = await update_beacon(
            beacon["beacon_id"],
            expected_state="monitoring",
            state="monitoring",
            current_car_distance=dist,
        )
        if updated:
            text, kb = render_monitoring(updated, plate)
            await _edit(bot, updated, text, kb)
    else:
        updated = await update_beacon(
            beacon["beacon_id"], expected_state="monitoring", state="gone")
        if updated:
            text, kb = render_gone(updated)
            await _edit(bot, updated, text, kb)


async def _handle_gone(bot: Bot, beacon: dict, cars: list, skipped: set, filt: str) -> None:
    # Immediately try to find another car
    nearby = find_cars_near(cars, beacon["lat"], beacon["lon"], beacon["radius"])
    if filt:
        nearby = [c for c in nearby if matches_filter(c["model"], filt)]
    nearby = [c for c in nearby if c["id"] not in skipped]

    if nearby:
        car = nearby[0]
        plate = await get_plate(car["id"])
        updated = await update_beacon(
            beacon["beacon_id"],
            expected_state="gone",
            state="found",
            current_car_id=car["id"],
            current_car_model=car["model"],
            current_car_distance=car["distance"],
            current_car_lat=car["lat"],
            current_car_lon=car["lon"],
            cars_found_count=beacon["cars_found_count"] + 1,
        )
        if updated:
            text, kb = render_found(updated, plate)
            await _edit(bot, updated, text, kb)
    else:
        updated = await update_beacon(
            beacon["beacon_id"], expected_state="gone", state="searching",
            current_car_id=None, current_car_model=None,
            current_car_distance=None, current_car_lat=None, current_car_lon=None)
        if updated:
            text, kb = render_searching(updated)
            await _edit(bot, updated, text, kb)


def _car_still_near(beacon: dict, cars: list, car_id: str | None) -> bool:
    if not car_id:
        return False
    for c in cars:
        if str(c.get("id")) == str(car_id):
            dist = haversine(beacon["lat"], beacon["lon"], c["lat"], c["lon"])
            return dist <= beacon["radius"]
    return False


async def _edit(bot: Bot, beacon: dict, text: str, kb) -> None:
    msg_id = beacon.get("message_id")
    chat_id = beacon.get("chat_id")
    if not msg_id or not chat_id:
        return
    try:
        await bot.edit_message_text(
            text, chat_id=chat_id, message_id=msg_id, reply_markup=kb)
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e):
            logger.warning("Edit failed for beacon {}: {}", beacon["beacon_id"], e)
    except Exception as e:
        logger.warning("Edit failed for beacon {}: {}", beacon["beacon_id"], e)
