from aiogram import Router

from handlers.callback import router as callback_router
from handlers.message import router as message_router
from handlers.admin import router as admin_router
from base.user_input import router as user_input_router

__all__ = ["router"]
router = Router()

router.include_routers(callback_router, user_input_router, message_router, admin_router)
