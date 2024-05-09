from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from telebot.util import quick_markup, chunks

from base.items import items_list
from helpers.utils import get_pager_controllers
from database.models import UserModel


class InlineMarkup:
    @classmethod
    def home_main(cls, user: UserModel) -> InlineKeyboardMarkup:
        return quick_markup(
            {"Действия": {"callback_data": f"actions choice {user.id}"}}
        )

    @classmethod
    def actions_choice(cls, user: UserModel) -> InlineKeyboardMarkup:
        def active_state_emoji(name):
            return "🔹" if user.state == name else ""

        markup = quick_markup(
            {
                f"Прогулка {active_state_emoji('street')}": {
                    "callback_data": f"actions street {user.id}"
                },
                f"Работа {active_state_emoji('work')}": {
                    "callback_data": f"actions work {user.id}"
                },
                f"Спать {active_state_emoji('sleep')}": {
                    "callback_data": f"actions sleep {user.id}"
                },
                f"Играть {active_state_emoji('game')}": {
                    "callback_data": f"actions game {user.id}"
                },
            }
        )

        markup.row(
            InlineKeyboardButton("Назад", callback_data=f"actions back {user.id}")
        )
        return markup

    @classmethod
    def update_action(cls, user: UserModel, name: str) -> InlineKeyboardMarkup:
        return quick_markup(
            {
                "Обновить": {"callback_data": f"actions {name} {user.id}"},
                "Назад": {"callback_data": f"actions choice {user.id}"},
            }
        )

    @classmethod
    def items_pager(cls, user: UserModel, index: int = 0) -> InlineKeyboardMarkup:
        items = list(chunks(items_list, 6))
        buttons = []

        for item in items[index]:
            buttons.append(
                InlineKeyboardButton(
                    f"{item.emoji} {item.name}",
                    callback_data=f"item_info {item.translit()} {index} {user.id}",
                )
            )

        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(*buttons)
        markup.row(*get_pager_controllers("item_info_main", pos=index, user_id=user.id))

        return markup
