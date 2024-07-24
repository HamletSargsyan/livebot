from typing import Type
from telebot.handler_backends import BaseMiddleware

from .register import RegisterMiddleware
from .actives import ActiveMiddleware


middlewares: list[Type[BaseMiddleware]] = [
    RegisterMiddleware,
    ActiveMiddleware,
]

__all__ = ["middlewares"]
