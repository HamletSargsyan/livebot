from typing import Union
from telebot import BaseMiddleware, CancelUpdate
from telebot.types import Message, CallbackQuery
from telebot.util import quick_markup

from helpers.utils import get_user_tag
from database.funcs import database
from database.models import UserModel

from config import TELEGRAM_ID, bot


def send_rules_message(message: Message, user: UserModel):
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

    bot.send_message(message.chat.id, mess, reply_markup=markup)


class RuleCheckMiddleware(BaseMiddleware):
    def __init__(self) -> None:
        self.update_types = ["message", "callback_query"]

    def pre_process(self, message: Message | CallbackQuery, data):
        if message.from_user.is_bot or message.from_user.id == TELEGRAM_ID:
            return CancelUpdate()
        user = database.users.get(id=message.from_user.id)

        if user.accepted_rules:
            return

        if isinstance(message, Message) and not message.text.startswith("/start"):
            send_rules_message(message, user)
            return CancelUpdate()
        elif isinstance(message, CallbackQuery) and not message.data.startswith(
            "accept_rules"
        ):
            send_rules_message(message.message, user)  # pyright: ignore
            return CancelUpdate()

    def post_process(self, message: Union[Message, CallbackQuery], data, exception):
        pass
