from telebot import BaseMiddleware, CancelUpdate
from telebot.types import Message

from helpers.advert import send_advert
from database.funcs import database


class AdvertMiddleware(BaseMiddleware):
    def __init__(self) -> None:
        self.update_types = ["message"]

    def pre_process(self, message: Message, data):
        if message.from_user.is_bot:
            return CancelUpdate()

    def post_process(self, message, data, exception):
        user = database.users.get(id=message.from_user.id)
        send_advert(message, user)
