from typing import Final

from aiogram.types import InlineKeyboardButton

COIN_EMOJI: Final = "🪙"


PAGER_CONTROLLERS: Final = [
    InlineKeyboardButton(text="↩️", callback_data="{name} start {pos} {user_id}"),
    InlineKeyboardButton(text="⬅️", callback_data="{name} back {pos} {user_id}"),
    InlineKeyboardButton(text="➡️", callback_data="{name} next {pos} {user_id}"),
    InlineKeyboardButton(text="↪️", callback_data="{name} end {pos} {user_id}"),
]
