from typing import Type
from telebot.handler_backends import BaseMiddleware

from .register import RegisterMiddleware
from .actives import ActiveMiddleware
from .rule_check import RuleCheckMiddleware

middlewares: list[Type[BaseMiddleware]] = [
    RegisterMiddleware,
    ActiveMiddleware,
    RuleCheckMiddleware,
]

__all__ = ["middlewares"]
