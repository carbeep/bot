from aiogram import Router

from src.handlers.start import router as start_router
from src.handlers.zones import router as zones_router
from src.handlers.cars import router as cars_router
from src.handlers.settings import router as settings_router
from src.handlers.plates import router as plates_router
from src.handlers.text import router as text_router


def setup_routers() -> Router:
    root = Router()
    root.include_router(start_router)
    root.include_router(zones_router)
    root.include_router(cars_router)
    root.include_router(settings_router)
    root.include_router(plates_router)
    root.include_router(text_router)  # catch-all last
    return root
