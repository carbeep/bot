"""Loguru setup: console + file with rotation. Intercepts stdlib logging."""

import logging
import sys
from pathlib import Path

from loguru import logger

LOG_DIR = Path(__file__).parent.parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)


class _InterceptHandler(logging.Handler):
    """Route stdlib logging → loguru."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno
        frame, depth = logging.currentframe(), 0
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1
        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def setup_logging() -> None:
    logger.remove()

    # Console: human-readable
    logger.add(
        sys.stderr,
        level="INFO",
        format="<green>{time:HH:mm:ss}</green> | <level>{level:<7}</level> | <cyan>{name}</cyan> | {message}",
    )

    # File: JSON, rotation 10MB, keep 7 days
    logger.add(
        LOG_DIR / "carbeep_{time:YYYY-MM-DD}.log",
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level:<7} | {name}:{function}:{line} | {message}",
        rotation="10 MB",
        retention="7 days",
        compression="gz",
        encoding="utf-8",
    )

    # Intercept stdlib logging (aiogram, asyncpg, aiohttp, etc.)
    logging.basicConfig(handlers=[_InterceptHandler()], level=logging.INFO, force=True)
    for name in ("aiogram", "asyncpg", "aiohttp", "redis"):
        logging.getLogger(name).handlers = [_InterceptHandler()]
