import asyncio
from typing import Any

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from loguru import logger

from src.core.redis.connection import cleanup_notified, mark_notified, was_notified
from src.repositories.plate_repo import get_plate
from src.repositories.user_repo import get_all_users
from src.repositories.zone_repo import get_active_zones
from src.services.delimobil import fetch_cars, find_cars_near, matches_filter, model_title
from src.services.geo import format_distance
from src.services.schedule import is_quiet_hours, is_zone_active_now
from src.settings import get_settings


async def poll_loop(bot: Bot) -> None:
    s = get_settings()
    logger.info("Poll loop started (interval=%ds)", s.POLL_INTERVAL)
    while True:
        try:
            await _tick(bot)
        except Exception:
            logger.exception("Poll tick error")
        await asyncio.sleep(s.POLL_INTERVAL)


async def _tick(bot: Bot) -> None:
    await cleanup_notified()
    users = await get_all_users()
    if not users:
        return

    by_region: dict[int, list[dict[str, Any]]] = {}
    for u in users:
        if not u["notifications_on"] or is_quiet_hours(u):
            continue
        by_region.setdefault(u["region_id"], []).append(u)

    for region_id, reg_users in by_region.items():
        cars = await fetch_cars(region_id)
        if not cars:
            continue
        for u in reg_users:
            uid = u["user_id"]
            filt = u["model_filter"] or ""
            for zone in await get_active_zones(uid):
                if not is_zone_active_now(zone):
                    continue
                nearby = find_cars_near(cars, zone["lat"], zone["lon"], zone["radius"])
                if filt:
                    nearby = [c for c in nearby if matches_filter(c["model"], filt)]
                new_cars = [c for c in nearby if not await was_notified(uid, c["id"])]
                if not new_cars:
                    continue
                for c in new_cars:
                    await mark_notified(uid, c["id"])
                await _notify(bot, uid, zone, new_cars)


async def _notify(bot: Bot, user_id: int, zone: dict[str, Any], cars: list[dict[str, Any]]) -> None:
    lines = [f"🚗 <b>Новые машины рядом с «{zone['name']}»!</b>\n"]
    buttons: list[list[InlineKeyboardButton]] = []
    for i, car in enumerate(cars[:10], 1):
        mt = model_title(car["model"])
        dist = format_distance(car["distance"])
        plate = await get_plate(car["id"])
        lines.append(f"{i}. {mt} — {dist}")
        if plate:
            buttons.append([InlineKeyboardButton(text=f"🔓 {mt}", url=f"delimobil://map/car/{plate}")])
        else:
            buttons.append([
                InlineKeyboardButton(text="🔓 Делимобиль", url="delimobil://map"),
                InlineKeyboardButton(text=f"📝 Госномер ({mt})", callback_data=f"report_plate:{car['id']}")])
    lines.append("\n📝 Знаешь госномер? Тапни кнопку.")
    try:
        await bot.send_message(user_id, "\n".join(lines), reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
        for car in cars[:5]:
            await bot.send_location(user_id, latitude=car["lat"], longitude=car["lon"])
    except Exception:
        logger.warning("Failed to notify user %d", user_id)
