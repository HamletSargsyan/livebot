from typing import Callable, Awaitable, Any
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject

from config import TELEGRAM_ID
from database.funcs import database
from helpers.utils import increment_achievement_progress, utcnow


class ActiveMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ):
        result = await handler(event, data)
        if isinstance(event, (Message, CallbackQuery)):
            if event.from_user.id == TELEGRAM_ID or event.from_user.is_bot:
                return

            user_id = event.from_user.id
            user = database.users.get(id=user_id)
            user.last_active_time = utcnow()
            database.users.update(**user.to_dict())

            if (utcnow() - user.registered_at).days >= 7:
                increment_achievement_progress(user, "новичок")
            return result
