"""Render beacon messages for each state."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from src.services.delimobil import model_title
from src.services.geo import format_distance

MSK = timezone(timedelta(hours=3))


def _now_str() -> str:
    return datetime.now(MSK).strftime("%H:%M:%S")


def _duration(beacon: dict[str, Any]) -> str:
    started = beacon.get("started_at")
    if not started:
        return "?"
    delta = datetime.now(timezone.utc) - started.replace(tzinfo=timezone.utc)
    mins = int(delta.total_seconds() // 60)
    if mins < 1:
        return "<1 мин"
    if mins < 60:
        return f"{mins} мин"
    return f"{mins // 60}ч {mins % 60}мин"


def _bid(beacon: dict[str, Any]) -> int:
    return beacon["beacon_id"]


# ---- SEARCHING ----

def render_searching(beacon: dict[str, Any]) -> tuple[str, InlineKeyboardMarkup]:
    r = format_distance(beacon["radius"])
    text = f"🔍 Ищу машины рядом ({r})\nОбновлено: {_now_str()}"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚙️ Радиус", callback_data=f"b:radius:{_bid(beacon)}"),
         InlineKeyboardButton(text="🔍 Фильтр", callback_data=f"b:filter:{_bid(beacon)}"),
         InlineKeyboardButton(text="⏹ Стоп", callback_data=f"b:stop:{_bid(beacon)}")],
    ])
    return text, kb


# ---- FOUND ----

def render_found(beacon: dict[str, Any], plate: str | None) -> tuple[str, InlineKeyboardMarkup]:
    model = model_title(beacon.get("current_car_model") or "Авто")
    dist = format_distance(beacon.get("current_car_distance") or 0)
    car_id = beacon.get("current_car_id") or ""
    bid = _bid(beacon)

    rows: list[list[InlineKeyboardButton]] = []

    if plate:
        text = f"🚗 Нашёл! {model} — {dist}\n🔑 {plate}"
        rows.append([InlineKeyboardButton(
            text=f"🔓 Забронировать {model}",
            url=f"https://app.delimobil.ru/auto/{plate}")])
    else:
        text = f"🚗 Нашёл! {model} — {dist}"
        rows.append([InlineKeyboardButton(
            text="📝 Сообщить госномер → получить ссылку",
            callback_data=f"b:plate:{bid}:{car_id}")])

    rows.append([
        InlineKeyboardButton(text="⏭ Пропустить", callback_data=f"b:skip:{bid}"),
        InlineKeyboardButton(text="⏹ Стоп", callback_data=f"b:stop:{bid}"),
    ])
    return text, InlineKeyboardMarkup(inline_keyboard=rows)


# ---- MONITORING ----

def render_monitoring(beacon: dict[str, Any], plate: str | None) -> tuple[str, InlineKeyboardMarkup]:
    model = model_title(beacon.get("current_car_model") or "Авто")
    dist = format_distance(beacon.get("current_car_distance") or 0)
    bid = _bid(beacon)
    car_id = beacon.get("current_car_id") or ""

    rows: list[list[InlineKeyboardButton]] = []

    if plate:
        text = f"✅ {model} ещё свободна — {dist}\n🔑 {plate} · Проверено: {_now_str()}"
        rows.append([InlineKeyboardButton(
            text=f"🔓 Забронировать {model}",
            url=f"https://app.delimobil.ru/auto/{plate}")])
    else:
        text = f"✅ {model} ещё свободна — {dist}\nПроверено: {_now_str()}"
        rows.append([InlineKeyboardButton(
            text="📝 Госномер → ссылка на бронь",
            callback_data=f"b:plate:{bid}:{car_id}")])

    rows.append([
        InlineKeyboardButton(text="⏭ Другую", callback_data=f"b:skip:{bid}"),
        InlineKeyboardButton(text="⏹ Стоп", callback_data=f"b:stop:{bid}"),
    ])
    return text, InlineKeyboardMarkup(inline_keyboard=rows)


# ---- GONE ----

def render_gone(beacon: dict[str, Any]) -> tuple[str, InlineKeyboardMarkup]:
    model = model_title(beacon.get("current_car_model") or "Авто")
    text = f"❌ {model} больше не доступна\nИщу другие машины..."
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏹ Стоп", callback_data=f"b:stop:{_bid(beacon)}")],
    ])
    return text, kb


# ---- STOPPED ----

def render_stopped(beacon: dict[str, Any]) -> tuple[str, InlineKeyboardMarkup]:
    count = beacon.get("cars_found_count", 0)
    dur = _duration(beacon)
    text = (
        f"⏹ Маячок остановлен\n"
        f"Нашёл машин: {count} · Работал: {dur}\n\n"
        f"📍 Отправь локацию — запущу снова"
    )
    return text, InlineKeyboardMarkup(inline_keyboard=[])


# ---- Radius picker ----

def render_radius_picker(beacon_id: int) -> tuple[str, InlineKeyboardMarkup]:
    text = "Выбери радиус поиска:"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="300м", callback_data=f"b:r:{beacon_id}:300"),
         InlineKeyboardButton(text="500м", callback_data=f"b:r:{beacon_id}:500")],
        [InlineKeyboardButton(text="1 км", callback_data=f"b:r:{beacon_id}:1000"),
         InlineKeyboardButton(text="2 км", callback_data=f"b:r:{beacon_id}:2000")],
        [InlineKeyboardButton(text="3 км", callback_data=f"b:r:{beacon_id}:3000")],
    ])
    return text, kb
