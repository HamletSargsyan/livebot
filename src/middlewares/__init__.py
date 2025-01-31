from typing import Type

from aiogram import BaseMiddleware

from middlewares.actives import ActiveMiddleware
from middlewares.register import RegisterMiddleware
from middlewares.rule_check import RuleCheckMiddleware

middlewares: list[Type[BaseMiddleware]] = [
    RegisterMiddleware,
    ActiveMiddleware,
    RuleCheckMiddleware,
]

__all__ = ["middlewares"]
