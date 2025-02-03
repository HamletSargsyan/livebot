from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from config import TELEGRAM_ID
from database.funcs import database
from helpers.datetime_utils import utcnow
from helpers.utils import increment_achievement_progress


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
            user = await database.users.async_get(id=user_id)

            last_active_time = user.last_active_time

            user.last_active_time = utcnow()
            await database.users.async_update(**user.to_dict())

            if (utcnow() - last_active_time).days >= 1:
                increment_achievement_progress(user, "новичок")
                increment_achievement_progress(user, "олд")
            return result
