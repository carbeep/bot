from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from src.repositories.user_repo import ensure_user, get_user, update_user
from src.repositories.zone_repo import get_user_zones
from src.settings import get_settings

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await ensure_user(message.from_user.id)
    await message.answer(
        "<b>Привет! Я Carbeep</b> — бот для мониторинга машин Делимобиля.\n\n"
        "Отправь мне <b>геолокацию</b> — я создам зону наблюдения. "
        "Как только рядом появится свободная машина — пришлю уведомление.\n\n"
        "<b>Команды:</b>\n"
        "/zones — мои зоны\n"
        "/now — машины рядом прямо сейчас\n"
        "/nearest — ближайшая машина\n"
        "/filter — фильтр по модели\n"
        "/schedule — расписание зон\n"
        "/settings — настройки\n"
        "/region — сменить город\n"
        "/plate — сообщить госномер\n"
        "/status — статус бота\n"
        "/help — справка\n"
        "/stop — отключить уведомления",
    )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(
        "<b>Справка Carbeep</b>\n\n"
        "1. Отправь <b>геолокацию</b> — создам зону наблюдения.\n"
        "2. Бот опрашивает Делимобиль каждые 15 сек.\n"
        "3. Новые машины в зонах → уведомление.\n\n"
        "Если знаешь госномер — нажми «📝 Сообщить госномер» в уведомлении.",
    )


@router.message(Command("stop"))
async def cmd_stop(message: Message) -> None:
    await ensure_user(message.from_user.id)
    await update_user(message.from_user.id, notifications_on=False)
    await message.answer("Уведомления <b>выключены</b>. Включить: /settings")


@router.message(Command("status"))
async def cmd_status(message: Message) -> None:
    await ensure_user(message.from_user.id)
    s = get_settings()
    user = await get_user(message.from_user.id)
    zones = await get_user_zones(message.from_user.id)
    active = sum(1 for z in zones if z["active"])
    region = s.REGIONS.get(user["region_id"], "?")
    notif = "вкл" if user["notifications_on"] else "выкл"
    filt = user["model_filter"] or "нет"
    qs, qe = user["quiet_start"], user["quiet_end"]
    quiet = f"{qs}:00–{qe}:00" if qs >= 0 and qe >= 0 else "нет"
    await message.answer(
        f"<b>Статус</b>\n\nРегион: {region}\nЗоны: {len(zones)} (активных: {active})\n"
        f"Уведомления: {notif}\nФильтр: {filt}\nТихие часы: {quiet}\n"
        f"Интервал: {s.POLL_INTERVAL}с",
    )
