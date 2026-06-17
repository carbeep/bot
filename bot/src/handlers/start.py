from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup

from src.repositories.beacon_repo import stop_user_beacons
from src.repositories.user_repo import ensure_user
from src.services.beacon_messages import render_stopped

router = Router()

_LOCATION_KB = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="📍 Отправить локацию", request_location=True)]],
    resize_keyboard=True, one_time_keyboard=True,
)


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await ensure_user(message.from_user.id)
    await message.answer(
        "<b>Carbeep</b> — мониторинг машин Делимобиля\n\n"
        "Отправь 📍 локацию — я запущу маячок и буду обновлять "
        "одно сообщение в реальном времени. Как только рядом появится "
        "свободная машина — покажу с кнопкой бронирования.\n\n"
        "/stop — остановить маячок\n"
        "/settings — город, фильтр моделей\n"
        "/help — справка",
        reply_markup=_LOCATION_KB,
    )


@router.message(Command("stop"))
async def cmd_stop(message: Message) -> None:
    await ensure_user(message.from_user.id)
    stopped = await stop_user_beacons(message.from_user.id)
    for b in stopped:
        if b.get("message_id") and b.get("chat_id"):
            text, kb = render_stopped(b)
            try:
                await message.bot.edit_message_text(
                    text, chat_id=b["chat_id"], message_id=b["message_id"], reply_markup=kb)
            except Exception:
                pass
    if stopped:
        await message.answer("⏹ Маячок остановлен.")
    else:
        await message.answer("Нет активных маячков. Отправь 📍 локацию.", reply_markup=_LOCATION_KB)


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(
        "<b>Как пользоваться</b>\n\n"
        "📍 Отправь локацию — запустится маячок.\n"
        "Одно сообщение обновляется в реальном времени:\n"
        "🔍 ищет → 🚗 нашёл → ✅ следит → ❌ уехала → 🔍 ищет дальше\n\n"
        "<b>Кнопки на маячке:</b>\n"
        "🔓 Забронировать — открыть машину в Делимобиле\n"
        "⏭ Пропустить — показать следующую\n"
        "⚙️ Радиус — изменить радиус поиска\n"
        "🔍 Фильтр — фильтр по модели\n"
        "⏹ Стоп — остановить\n\n"
        "/stop — остановить маячок\n"
        "/settings — город, фильтр",
        reply_markup=_LOCATION_KB,
    )
