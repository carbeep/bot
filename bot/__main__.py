"""Entry point: python -m bot"""

import asyncio

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
from loguru import logger

from src.core.db.connection import close_pool, create_pool
from src.core.logger import setup_logging
from src.core.redis.connection import close_redis, create_redis
from src.handlers import setup_routers
from src.poller import poll_loop
from src.settings import get_settings


async def on_startup(bot: Bot) -> None:
    await create_redis()
    await create_pool()
    asyncio.create_task(poll_loop(bot))
    s = get_settings()
    logger.info("Bot started. region={} ({}), poll={}s",
                s.REGION_ID, s.REGIONS.get(s.REGION_ID, "?"), s.POLL_INTERVAL)


async def on_shutdown(bot: Bot) -> None:
    await close_pool()
    await close_redis()
    logger.info("Bot stopped.")


def main() -> None:
    setup_logging()
    s = get_settings()
    if not s.BOT_TOKEN.get_secret_value():
        raise SystemExit("CARBEEP_BOT_TOKEN env var is required. See .env.example")

    storage = RedisStorage.from_url(s.REDIS_URL)
    bot = Bot(token=s.BOT_TOKEN.get_secret_value(),
              default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=storage)
    dp.include_router(setup_routers())
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    dp.run_polling(bot)


if __name__ == "__main__":
    main()
