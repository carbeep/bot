from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from src.repositories.user_repo import ensure_user, get_user, update_user
from src.settings import get_settings

router = Router()


class FilterStates(StatesGroup):
    waiting_filter = State()


@router.message(Command("settings"))
async def cmd_settings(message: Message) -> None:
    await ensure_user(message.from_user.id)
    user = await get_user(message.from_user.id)
    s = get_settings()
    region = s.REGIONS.get(user["region_id"], "?")
    filt = user["model_filter"] or "все модели"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"🏙 Город: {region}", callback_data="s:region")],
        [InlineKeyboardButton(text=f"🔍 Фильтр: {filt}", callback_data="s:filter")],
    ])
    await message.answer("<b>Настройки</b>", reply_markup=kb)


@router.callback_query(F.data == "s:region")
async def cb_region_menu(callback: CallbackQuery) -> None:
    s = get_settings()
    buttons, row = [], []
    for rid, name in sorted(s.REGIONS.items(), key=lambda x: x[1]):
        row.append(InlineKeyboardButton(text=name, callback_data=f"s:r:{rid}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    await callback.message.edit_text("Выбери город:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()


@router.callback_query(F.data.startswith("s:r:"))
async def cb_region_set(callback: CallbackQuery) -> None:
    rid = int(callback.data.split(":")[2])
    await update_user(callback.from_user.id, region_id=rid)
    await callback.message.edit_text(f"Город: <b>{get_settings().REGIONS.get(rid, rid)}</b>")
    await callback.answer()


@router.callback_query(F.data == "s:filter")
async def cb_filter_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(FilterStates.waiting_filter)
    user = await get_user(callback.from_user.id)
    filt = user["model_filter"] or "нет"
    await callback.message.answer(
        f"Текущий фильтр: <b>{filt}</b>\n\n"
        "Введи модели через запятую (<code>kia, rio</code>).\n"
        "<code>-</code> — сбросить.")
    await callback.answer()


@router.message(FilterStates.waiting_filter)
async def handle_filter(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if text == "-":
        text = ""
    await update_user(message.from_user.id, model_filter=text)
    await state.clear()
    await message.answer(f"Фильтр: <b>{text or 'все модели'}</b>")
