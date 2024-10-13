from telebot import BaseMiddleware, CancelUpdate
from telebot.types import Message

from helpers.utils import from_user, remove_not_allowed_symbols

from database.funcs import database
from database.models import UserModel
from config import logger


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
    def __init__(self) -> None:
        self.update_types = ["message"]

    def pre_process(self, message: Message, data):
        if from_user(message).is_bot:
            return CancelUpdate()
        register_user(message)

        if message.reply_to_message:
            if from_user(message.reply_to_message).is_bot:
                return CancelUpdate()
            register_user(message.reply_to_message)

    def post_process(self, message, data, exception):
        pass
