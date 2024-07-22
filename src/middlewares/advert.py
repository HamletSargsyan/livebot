from typing_extensions import deprecated
import requests
from telebot import BaseMiddleware, CancelUpdate
from telebot.types import Message

from helpers.advert import send_advert
from database.funcs import database


@deprecated("Deprecated", category=DeprecationWarning)
class AdvertMiddleware(BaseMiddleware):
    def __init__(self) -> None:
        self.update_types = ["message"]

    def pre_process(self, message: Message, data):
        if message.from_user.is_bot:
            return CancelUpdate()

    def post_process(self, message: Message, data, exception):
        if str(message.text).startswith("/start"):
            return
        user = database.users.get(id=message.from_user.id)
        try:
            send_advert(message, user)
        except requests.exceptions.JSONDecodeError as e:
            raise Exception(f"Cant send advert to `{user.id}`") from e
