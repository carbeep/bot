from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from src.repositories.user_repo import ensure_user, get_user, update_user
from src.settings import get_settings

router = Router()


class SettingsStates(StatesGroup):
    waiting_quiet_start = State()
    waiting_quiet_end = State()


class FilterStates(StatesGroup):
    waiting_filter = State()


@router.message(Command("region"))
async def cmd_region(message: Message) -> None:
    await ensure_user(message.from_user.id)
    s = get_settings()
    buttons, row = [], []
    for rid, name in sorted(s.REGIONS.items(), key=lambda x: x[1]):
        row.append(InlineKeyboardButton(text=name, callback_data=f"region:{rid}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    await message.answer("Выбери город:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@router.callback_query(F.data.startswith("region:"))
async def cb_region(callback: CallbackQuery) -> None:
    rid = int(callback.data.split(":")[1])
    await update_user(callback.from_user.id, region_id=rid)
    await callback.message.edit_text(f"Регион: <b>{get_settings().REGIONS.get(rid, rid)}</b>")
    await callback.answer()


@router.message(Command("filter"))
async def cmd_filter(message: Message, state: FSMContext) -> None:
    await ensure_user(message.from_user.id)
    user = await get_user(message.from_user.id)
    await state.set_state(FilterStates.waiting_filter)
    await message.answer(
        f"Фильтр: <b>{user['model_filter'] or 'нет'}</b>\n\n"
        "Введи модели через запятую (<code>kia, rio</code>). <code>-</code> — сбросить.")


@router.message(FilterStates.waiting_filter)
async def handle_filter(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if text == "-":
        text = ""
    await update_user(message.from_user.id, model_filter=text)
    await state.clear()
    await message.answer(f"Фильтр: <b>{text or 'все модели'}</b>")


@router.message(Command("settings"))
async def cmd_settings(message: Message) -> None:
    await ensure_user(message.from_user.id)
    user = await get_user(message.from_user.id)
    notif = user["notifications_on"]
    qs, qe = user["quiet_start"], user["quiet_end"]
    quiet = f"{qs}:00–{qe}:00" if qs >= 0 and qe >= 0 else "нет"
    buttons = [
        [InlineKeyboardButton(text=f"{'🔕 Выкл' if notif else '🔔 Вкл'} уведомления", callback_data="s:toggle")],
        [InlineKeyboardButton(text=f"🌙 Тихие часы ({quiet})", callback_data="s:quiet")],
        [InlineKeyboardButton(text="❌ Сбросить тихие часы", callback_data="s:quiet_reset")],
    ]
    await message.answer(
        f"<b>Настройки</b>\n\nУведомления: {'вкл 🔔' if notif else 'выкл 🔕'}\nТихие часы: {quiet}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@router.callback_query(F.data == "s:toggle")
async def cb_toggle(callback: CallbackQuery) -> None:
    user = await get_user(callback.from_user.id)
    new = not user["notifications_on"]
    await update_user(callback.from_user.id, notifications_on=new)
    await callback.answer("🔔 Вкл" if new else "🔕 Выкл")
    await cmd_settings(callback.message)


@router.callback_query(F.data == "s:quiet")
async def cb_quiet(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(SettingsStates.waiting_quiet_start)
    await callback.message.answer("Час <b>начала</b> тихих часов (0–23, МСК):")
    await callback.answer()


@router.message(SettingsStates.waiting_quiet_start)
async def handle_quiet_start(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if not text.isdigit() or not (0 <= int(text) <= 23):
        await message.answer("Число от 0 до 23.")
        return
    await state.update_data(quiet_start=int(text))
    await state.set_state(SettingsStates.waiting_quiet_end)
    await message.answer("Час <b>конца</b> тихих часов (0–23, МСК):")


@router.message(SettingsStates.waiting_quiet_end)
async def handle_quiet_end(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if not text.isdigit() or not (0 <= int(text) <= 23):
        await message.answer("Число от 0 до 23.")
        return
    data = await state.get_data()
    qs, qe = data["quiet_start"], int(text)
    await update_user(message.from_user.id, quiet_start=qs, quiet_end=qe)
    await state.clear()
    await message.answer(f"Тихие часы: <b>{qs}:00–{qe}:00</b> МСК")


@router.callback_query(F.data == "s:quiet_reset")
async def cb_quiet_reset(callback: CallbackQuery) -> None:
    await update_user(callback.from_user.id, quiet_start=-1, quiet_end=-1)
    await callback.answer("Сброшено")
    await cmd_settings(callback.message)
