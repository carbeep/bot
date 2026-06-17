from aiogram import F, Router
from aiogram.types import Message

from src.core.redis.connection import get_pending_plate, pop_pending_plate
from src.repositories.plate_repo import find_plate_by_number, save_plate
from src.services.plates import display, is_valid, normalize

router = Router()


@router.message(F.text)
async def handle_text(message: Message) -> None:
    uid = message.from_user.id
    text = (message.text or "").strip()

    car_id = await get_pending_plate(uid)
    if car_id:
        if is_valid(text):
            plate = normalize(text)
            await save_plate(car_id, plate, uid)
            await pop_pending_plate(uid)
            await message.answer(f"Госномер <b>{display(plate)}</b> сохранён для машины {car_id}. Спасибо!")
        else:
            await message.answer("Не похоже на госномер. Формат: <code>А123ВС77</code>.")
        return

    if is_valid(text):
        plate = normalize(text)
        existing = await find_plate_by_number(plate)
        if existing:
            await message.answer(f"Госномер <b>{display(plate)}</b> уже привязан к машине {existing}.")
        else:
            await message.answer(f"Похоже на госномер: <b>{display(plate)}</b>.\n"
                                 "Нажми «📝 Сообщить госномер» в уведомлении чтобы привязать.")
        return

    await message.answer("Не понимаю. /help — команды, или отправь геолокацию.")
