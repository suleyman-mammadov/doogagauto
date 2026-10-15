from bot.handlers.filter_fsm import router as filter_router
from bot.handlers.management import router as management_router
from bot.handlers.admin import router as admin_router

__all__ = ["filter_router", "management_router", "admin_router"]
