from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, KeyboardButton, Message, ReplyKeyboardMarkup

from src.core.redis.connection import set_pending_plate
from src.repositories.beacon_repo import (
    add_skipped_car, create_beacon, get_user_beacon,
    set_message_id, stop_beacon, stop_user_beacons, update_beacon,
)
from src.repositories.plate_repo import get_plate
from src.repositories.user_repo import ensure_user, get_user
from src.services.beacon_messages import (
    render_found, render_monitoring, render_radius_picker,
    render_searching, render_stopped,
)

router = Router()


class BeaconFilterState(StatesGroup):
    waiting_filter = State()


# ---- Location → start beacon ----

@router.message(F.location)
async def handle_location(message: Message) -> None:
    uid = message.from_user.id
    await ensure_user(uid)
    user = await get_user(uid)

    # Stop existing beacons
    old = await stop_user_beacons(uid)
    for b in old:
        if b.get("message_id") and b.get("chat_id"):
            text, kb = render_stopped(b)
            try:
                await message.bot.edit_message_text(
                    text, chat_id=b["chat_id"], message_id=b["message_id"],
                    reply_markup=kb)
            except Exception:
                pass

    # Create new beacon
    beacon = await create_beacon(
        user_id=uid,
        chat_id=message.chat.id,
        lat=message.location.latitude,
        lon=message.location.longitude,
        model_filter=user.get("model_filter") or "",
    )

    text, kb = render_searching(beacon)
    sent = await message.answer(text, reply_markup=kb)
    await set_message_id(beacon["beacon_id"], sent.message_id)


# ---- Stop ----

@router.callback_query(F.data.startswith("b:stop:"))
async def cb_stop(callback: CallbackQuery) -> None:
    beacon_id = int(callback.data.split(":")[2])
    beacon = await stop_beacon(beacon_id)
    if beacon:
        text, kb = render_stopped(beacon)
        try:
            await callback.message.edit_text(text, reply_markup=kb)
        except Exception:
            pass
    await callback.answer("Маячок остановлен")


# ---- Skip ----

@router.callback_query(F.data.startswith("b:skip:"))
async def cb_skip(callback: CallbackQuery) -> None:
    beacon_id = int(callback.data.split(":")[2])
    beacon = await get_user_beacon(callback.from_user.id)
    if not beacon or beacon["beacon_id"] != beacon_id:
        await callback.answer("Маячок не найден")
        return

    car_id = beacon.get("current_car_id")
    if car_id:
        await add_skipped_car(beacon_id, car_id)

    beacon = await update_beacon(
        beacon_id,
        state="searching",
        current_car_id=None,
        current_car_model=None,
        current_car_distance=None,
        current_car_lat=None,
        current_car_lon=None,
    )
    if beacon:
        text, kb = render_searching(beacon)
        try:
            await callback.message.edit_text(text, reply_markup=kb)
        except Exception:
            pass
    await callback.answer("Ищу другую")


# ---- Radius ----

@router.callback_query(F.data.startswith("b:radius:"))
async def cb_radius_menu(callback: CallbackQuery) -> None:
    beacon_id = int(callback.data.split(":")[2])
    text, kb = render_radius_picker(beacon_id)
    try:
        await callback.message.edit_text(text, reply_markup=kb)
    except Exception:
        pass
    await callback.answer()


@router.callback_query(F.data.startswith("b:r:"))
async def cb_radius_set(callback: CallbackQuery) -> None:
    parts = callback.data.split(":")
    beacon_id, radius = int(parts[2]), int(parts[3])
    beacon = await update_beacon(beacon_id, radius=radius, state="searching",
                                 current_car_id=None, current_car_model=None,
                                 current_car_distance=None, current_car_lat=None,
                                 current_car_lon=None)
    if beacon:
        text, kb = render_searching(beacon)
        try:
            await callback.message.edit_text(text, reply_markup=kb)
        except Exception:
            pass
    await callback.answer(f"Радиус: {radius}м")


# ---- Filter ----

@router.callback_query(F.data.startswith("b:filter:"))
async def cb_filter_menu(callback: CallbackQuery, state: FSMContext) -> None:
    beacon_id = int(callback.data.split(":")[2])
    await state.set_state(BeaconFilterState.waiting_filter)
    await state.update_data(filter_beacon_id=beacon_id)
    await callback.message.answer(
        "Введи модели через запятую (<code>kia, rio</code>).\n"
        "<code>-</code> — сбросить фильтр.")
    await callback.answer()


@router.message(BeaconFilterState.waiting_filter)
async def handle_filter_input(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    beacon_id = data.get("filter_beacon_id")
    text = (message.text or "").strip()
    if text == "-":
        text = ""
    await state.clear()

    if beacon_id:
        beacon = await update_beacon(beacon_id, model_filter=text)
        if beacon:
            await message.answer(f"Фильтр: <b>{text or 'все модели'}</b>")


# ---- Plate report from beacon ----

@router.callback_query(F.data.startswith("b:plate:"))
async def cb_plate_report(callback: CallbackQuery) -> None:
    parts = callback.data.split(":")
    car_id = parts[3] if len(parts) > 3 else ""
    if not car_id:
        await callback.answer("Ошибка")
        return

    existing = await get_plate(car_id)
    if existing:
        from src.services.plates import display
        await callback.answer(f"Уже записан: {display(existing)}", show_alert=True)
        return

    await set_pending_plate(callback.from_user.id, car_id)
    await callback.message.answer(
        f"Введи госномер для машины <b>{car_id}</b>.\n"
        f"Например: <code>Р074РС76</code>")
    await callback.answer()
