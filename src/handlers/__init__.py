from aiogram import F, Router
from aiogram.types import ErrorEvent, Message

from base.user_input import router as user_input_router
from handlers.admin import router as admin_router
from handlers.callback import router as callback_router
from handlers.message import router as message_router

__all__ = ["router"]
router = Router()

router.include_routers(callback_router, user_input_router, admin_router, message_router)


@router.error(F.update.message.as_("message"))
async def error_handler(event: ErrorEvent, message: Message):  # pylint: disable=unused-argument
    if not message:
        return

    mess = (
        "😰 Ой-ой, произошла ошибка.\n\n"
        "Сообщи об этом @HamletSargsyan или создай issue на github: "
        "https://github.com/HamletSargsyan/livebot/issues"
    )
    await message.reply(mess)
