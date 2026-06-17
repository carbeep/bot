from aiogram import Router
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from src.repositories.plate_repo import get_plate
from src.repositories.user_repo import ensure_user, get_user
from src.repositories.zone_repo import get_active_zones
from src.services.delimobil import fetch_cars, find_cars_near, matches_filter, model_title
from src.services.geo import format_distance

router = Router()


@router.message(Command("now"))
async def cmd_now(message: Message) -> None:
    await ensure_user(message.from_user.id)
    user = await get_user(message.from_user.id)
    zones = await get_active_zones(message.from_user.id)
    if not zones:
        await message.answer("Нет активных зон. Отправь геолокацию.")
        return

    cars = await fetch_cars(user["region_id"])
    if not cars:
        await message.answer("Не удалось получить данные. Попробуй позже.")
        return

    filt = user["model_filter"] or ""
    found = False
    for zone in zones:
        nearby = find_cars_near(cars, zone["lat"], zone["lon"], zone["radius"])
        if filt:
            nearby = [c for c in nearby if matches_filter(c["model"], filt)]
        if not nearby:
            continue
        found = True
        lines = [f"<b>📍 {zone['name']}</b> ({format_distance(zone['radius'])}):"]
        buttons = []
        for i, car in enumerate(nearby[:10], 1):
            mt = model_title(car["model"])
            dist = format_distance(car["distance"])
            plate = await get_plate(car["id"])
            lines.append(f"{i}. {mt} — {dist}")
            if plate:
                buttons.append([InlineKeyboardButton(text=f"🔓 {mt}", url=f"delimobil://map/car/{plate}")])
            else:
                buttons.append([
                    InlineKeyboardButton(text="🔓 Делимобиль", url="delimobil://map"),
                    InlineKeyboardButton(text="📝 Госномер", callback_data=f"report_plate:{car['id']}")])
        await message.answer("\n".join(lines), reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

    if not found:
        await message.answer("Сейчас машин в зонах нет.")


@router.message(Command("nearest"))
async def cmd_nearest(message: Message) -> None:
    await ensure_user(message.from_user.id)
    user = await get_user(message.from_user.id)
    zones = await get_active_zones(message.from_user.id)
    if not zones:
        await message.answer("Нет активных зон.")
        return
    cars = await fetch_cars(user["region_id"])
    if not cars:
        await message.answer("Не удалось получить данные.")
        return
    filt = user["model_filter"] or ""
    lines = ["<b>Ближайшие машины:</b>\n"]
    for zone in zones:
        nearby = find_cars_near(cars, zone["lat"], zone["lon"], 10_000)
        if filt:
            nearby = [c for c in nearby if matches_filter(c["model"], filt)]
        if nearby:
            car = nearby[0]
            lines.append(f"📍 <b>{zone['name']}</b>: {model_title(car['model'])} — {format_distance(car['distance'])}")
        else:
            lines.append(f"📍 <b>{zone['name']}</b>: нет поблизости")
    await message.answer("\n".join(lines))
