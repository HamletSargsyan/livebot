from typing import Type
from telebot.handler_backends import BaseMiddleware

from .register import RegisterMiddleware
from .advert import AdvertMiddleware


middlewares: list[Type[BaseMiddleware]] = [RegisterMiddleware, AdvertMiddleware]

__all__ = ["middlewares"]
