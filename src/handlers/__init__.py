from aiogram import Router

from handlers.callback import router as callback_router
from handlers.message import router as message_router
from handlers.admin import router as admin_router


router = Router()

router.include_routers(callback_router, message_router, admin_router)

__all__ = ["router"]
