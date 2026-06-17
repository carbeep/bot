from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from src.core.redis.connection import set_pending_plate
from src.repositories.plate_repo import get_plate
from src.services.plates import display

router = Router()


@router.message(Command("plate"))
async def cmd_plate(message: Message) -> None:
    await message.answer(
        "<b>Как сообщить госномер</b>\n\n"
        "1. Получи уведомление о машине.\n"
        "2. Нажми <b>«📝 Сообщить госномер»</b>.\n"
        "3. Отправь номер (<code>Р074РС76</code> или <code>P074PC76</code>).\n\n"
        "После этого все получат кнопку прямого бронирования.")


@router.callback_query(F.data.startswith("report_plate:"))
async def cb_report_plate(callback: CallbackQuery) -> None:
    car_id = callback.data.split(":", 1)[1]
    existing = await get_plate(car_id)
    if existing:
        await callback.answer(f"Уже записан: {display(existing)}", show_alert=True)
        return
    await set_pending_plate(callback.from_user.id, car_id)
    await callback.message.answer(
        f"Введи госномер для машины <b>{car_id}</b>.\nНапример: <code>Р074РС76</code>")
    await callback.answer()
