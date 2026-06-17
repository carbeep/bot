from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup,
    KeyboardButton, Message, ReplyKeyboardMarkup,
)

from src.core.redis.connection import set_next_zone_name, pop_next_zone_name
from src.repositories.user_repo import ensure_user
from src.repositories.zone_repo import (
    create_zone, delete_zone, get_user_zones,
    rename_zone, set_zone_schedule, toggle_zone,
)
from src.services.geo import format_distance

router = Router()


class ZoneStates(StatesGroup):
    waiting_rename = State()


class ScheduleStates(StatesGroup):
    waiting_schedule = State()


@router.message(Command("home"))
async def cmd_home(message: Message) -> None:
    await ensure_user(message.from_user.id)
    await set_next_zone_name(message.from_user.id, "Дом")
    await message.answer(
        "Отправь геолокацию для зоны <b>«Дом»</b>.",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="📍 Отправить", request_location=True)]],
            resize_keyboard=True, one_time_keyboard=True))


@router.message(Command("work"))
async def cmd_work(message: Message) -> None:
    await ensure_user(message.from_user.id)
    await set_next_zone_name(message.from_user.id, "Работа")
    await message.answer(
        "Отправь геолокацию для зоны <b>«Работа»</b>.",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="📍 Отправить", request_location=True)]],
            resize_keyboard=True, one_time_keyboard=True))


@router.message(F.location)
async def handle_location(message: Message, state: FSMContext) -> None:
    await ensure_user(message.from_user.id)
    lat, lon = message.location.latitude, message.location.longitude
    name = await pop_next_zone_name(message.from_user.id) or "Зона"

    await state.update_data(pending_lat=lat, pending_lon=lon, pending_name=name)
    buttons = [
        [InlineKeyboardButton(text="300м", callback_data="radius:300"),
         InlineKeyboardButton(text="500м", callback_data="radius:500")],
        [InlineKeyboardButton(text="1 км", callback_data="radius:1000"),
         InlineKeyboardButton(text="2 км", callback_data="radius:2000")],
        [InlineKeyboardButton(text="3 км", callback_data="radius:3000")],
    ]
    await message.answer(
        f"Локация получена. Радиус для <b>«{name}»</b>:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@router.callback_query(F.data.startswith("radius:"))
async def cb_radius(callback: CallbackQuery, state: FSMContext) -> None:
    radius = int(callback.data.split(":")[1])
    data = await state.get_data()
    lat, lon = data.get("pending_lat"), data.get("pending_lon")
    name = data.get("pending_name", "Зона")
    if lat is None:
        await callback.answer("Отправь геолокацию ещё раз.", show_alert=True)
        return
    zone_id = await create_zone(callback.from_user.id, lat, lon, radius, name)
    await state.clear()
    await callback.message.edit_text(
        f"✅ Зона <b>«{name}»</b> создана (#{zone_id}, {format_distance(radius)}).")
    await callback.answer()


@router.message(Command("zones"))
async def cmd_zones(message: Message) -> None:
    await ensure_user(message.from_user.id)
    zones = await get_user_zones(message.from_user.id)
    if not zones:
        await message.answer("Нет зон. Отправь геолокацию.")
        return
    lines = ["<b>Твои зоны:</b>\n"]
    buttons = []
    for z in zones:
        st = "✅" if z["active"] else "⏸"
        sched = f" ⏰ {z['schedule']}" if z["schedule"] else ""
        lines.append(f"{st} <b>{z['name']}</b> (#{z['zone_id']}) — {format_distance(z['radius'])}{sched}")
        buttons.append([
            InlineKeyboardButton(text=f"{'⏸' if z['active'] else '▶️'} {z['name']}", callback_data=f"ztoggle:{z['zone_id']}"),
            InlineKeyboardButton(text="✏️", callback_data=f"zrename:{z['zone_id']}"),
            InlineKeyboardButton(text="🗑", callback_data=f"zdelete:{z['zone_id']}")])
    await message.answer("\n".join(lines), reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@router.callback_query(F.data.startswith("ztoggle:"))
async def cb_toggle(callback: CallbackQuery) -> None:
    zone_id = int(callback.data.split(":")[1])
    result = await toggle_zone(zone_id, callback.from_user.id)
    await callback.answer("✅" if result else "⏸" if result is not None else "Не найдено")
    await cmd_zones(callback.message)


@router.callback_query(F.data.startswith("zdelete:"))
async def cb_delete(callback: CallbackQuery) -> None:
    await delete_zone(int(callback.data.split(":")[1]), callback.from_user.id)
    await callback.answer("Удалено")
    await cmd_zones(callback.message)


@router.callback_query(F.data.startswith("zrename:"))
async def cb_rename_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(ZoneStates.waiting_rename)
    await state.update_data(rename_zone_id=int(callback.data.split(":")[1]))
    await callback.message.answer("Введи новое имя:")
    await callback.answer()


@router.message(ZoneStates.waiting_rename)
async def handle_rename(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    zone_id = data.get("rename_zone_id")
    name = (message.text or "").strip()[:50] or "Зона"
    if zone_id:
        await rename_zone(zone_id, message.from_user.id, name)
        await message.answer(f"Зона #{zone_id} → <b>«{name}»</b>")
    await state.clear()


@router.message(Command("schedule"))
async def cmd_schedule(message: Message) -> None:
    await ensure_user(message.from_user.id)
    zones = await get_user_zones(message.from_user.id)
    if not zones:
        await message.answer("Сначала создай зону.")
        return
    buttons = [[InlineKeyboardButton(
        text=f"⏰ «{z['name']}» ({z['schedule'] or 'всегда'})",
        callback_data=f"zsched:{z['zone_id']}")] for z in zones]
    await message.answer(
        "<b>Расписание</b>\n\nФормат: <code>days:0,1,2,3,4;hours:8-20</code>\n"
        "(0=Пн..6=Вс, МСК). <code>-</code> для сброса.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@router.callback_query(F.data.startswith("zsched:"))
async def cb_schedule_zone(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(ScheduleStates.waiting_schedule)
    await state.update_data(sched_zone_id=int(callback.data.split(":")[1]))
    await callback.message.answer("Введи расписание:")
    await callback.answer()


@router.message(ScheduleStates.waiting_schedule)
async def handle_schedule(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    zone_id = data.get("sched_zone_id")
    text = (message.text or "").strip()
    if text == "-":
        text = ""
    if zone_id:
        await set_zone_schedule(zone_id, message.from_user.id, text)
        await message.answer(f"Расписание #{zone_id}: <b>{text or 'всегда'}</b>")
    await state.clear()
