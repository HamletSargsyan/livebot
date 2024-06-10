from typing import Type
from telebot.handler_backends import BaseMiddleware

from .register import RegisterMiddleware
from .advert import AdvertMiddleware
from .actives import ActiveMiddleware


middlewares: list[Type[BaseMiddleware]] = [
    RegisterMiddleware,
    AdvertMiddleware,
    ActiveMiddleware,
]

__all__ = ["middlewares"]
