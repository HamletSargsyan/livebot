from aiogram import Router

from base.user_input import router as user_input_router
from handlers.admin import router as admin_router
from handlers.callback import router as callback_router
from handlers.message import router as message_router

__all__ = ["router"]
router = Router()

router.include_routers(callback_router, user_input_router, admin_router, message_router)
