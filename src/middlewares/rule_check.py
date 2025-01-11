from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from config import TELEGRAM_ID
from database.funcs import database
from database.models import UserModel
from helpers.utils import get_user_tag, quick_markup


async def send_rules_message(message: Message, user: UserModel):
    mess = f"{get_user_tag(user)}, перед там как использовать бота, ты должен прочитать правила"
    markup = quick_markup(
        {
            "Читать": {"url": "https://hamletsargsyan.github.io/livebot/rules"},
            "Я прочитал и полностью согласен с правилами": {
                "callback_data": f"accept_rules {user.id}"
            },
        },
        row_width=1,
    )

    await message.answer(mess, reply_markup=markup)


class RuleCheckMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ):
        if isinstance(event, (Message, CallbackQuery)):
            if event.from_user.id == TELEGRAM_ID or event.from_user.is_bot:
                return

            user = database.users.get(id=event.from_user.id)

            if user.accepted_rules:
                return

            if isinstance(event, Message) and not event.text.startswith("/start"):
                await send_rules_message(event, user)
                return
            if isinstance(event, CallbackQuery) and not event.data.startswith("accept_rules"):
                await send_rules_message(event.message, user)  # pyright: ignore
                return

        return await handler(event, data)
