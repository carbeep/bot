from aiogram import Router

from src.handlers.start import router as start_router
from src.handlers.beacon import router as beacon_router
from src.handlers.settings import router as settings_router
from src.handlers.plates import router as plates_router
from src.handlers.text import router as text_router


def setup_routers() -> Router:
    root = Router()
    root.include_router(start_router)
    root.include_router(beacon_router)
    root.include_router(settings_router)
    root.include_router(plates_router)
    root.include_router(text_router)  # catch-all last
    return root
