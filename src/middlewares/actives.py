from typing import Union
from telebot import BaseMiddleware, CancelUpdate
from telebot.types import Message, CallbackQuery

from database.funcs import database
from helpers.utils import utcnow


class ActiveMiddleware(BaseMiddleware):
    def __init__(self) -> None:
        self.update_types = ["message", "callback_query"]

    def pre_process(self, message: Union[Message, CallbackQuery], data):
        if message.from_user.is_bot:  # type: ignore
            return CancelUpdate()

    def post_process(self, message: Union[Message, CallbackQuery], data, exception):
        user_id = message.from_user.id  # type: ignore
        user = database.users.get(id=user_id)
        user.last_active_time = utcnow()
        database.users.update(**user.to_dict())
