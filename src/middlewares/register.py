from typing import Any, Awaitable, Callable
from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject

from helpers.utils import from_user, remove_not_allowed_symbols

from database.funcs import database
from database.models import UserModel
from config import TELEGRAM_ID, logger


def register_user(message: Message):
    user = database.users.check_exists(id=from_user(message).id)
    if not user:
        user = UserModel(
            id=from_user(message).id,
            name=remove_not_allowed_symbols(from_user(message).full_name),
        )
        database.users.add(**user.to_dict())
        logger.info(f"Новый пользователь: {user.name} ({user.id})")


class RegisterMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ):
        if isinstance(event, Message):
            if event.from_user.id == TELEGRAM_ID or event.from_user.is_bot:
                return

            register_user(event)
            if event.reply_to_message:
                register_user(event.reply_to_message)
            return await handler(event, data)
