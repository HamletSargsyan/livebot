from telebot import BaseMiddleware, CancelUpdate
from telebot.types import Message

from helpers.utils import remove_not_allowed_symbols

from database.funcs import database
from database.models import UserModel
from config import logger


def register_user(message: Message):
    user = database.users.check_exists(id=message.from_user.id)
    if not user:
        user = UserModel(
            id=message.from_user.id,
            name=remove_not_allowed_symbols(message.from_user.full_name),
            username=message.from_user.username,
        )
        database.users.add(**user.to_dict())
        logger.info(f"Новый пользователь: {user.name} ({user.id})")


class RegisterMiddleware(BaseMiddleware):
    def __init__(self) -> None:
        self.update_types = ["message"]

    def pre_process(self, message: Message, data):
        if message.from_user.is_bot:
            return CancelUpdate()
        register_user(message)

        if message.reply_to_message:
            if message.reply_to_message.from_user.is_bot:
                return CancelUpdate()
            register_user(message.reply_to_message)

    def post_process(self, message, data, exception):
        pass
