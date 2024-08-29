from copy import deepcopy
from typing import Literal
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from telebot.util import quick_markup, chunks

from base.achievements import ACHIEVEMENTS
from base.items import items_list
from helpers.utils import (
    achievement_status,
    get_item_emoji,
    get_pager_controllers,
    get_time_difference_string,
    is_completed_achievement,
    utcnow,
)
from database.models import DailyGiftModel, MarketItemModel, UserModel
from database.funcs import database

from config import logger


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

    @classmethod
    def market_pager(cls, user: UserModel, index: int = 0) -> InlineKeyboardMarkup:
        market_items = sorted(
            database.market_items.get_all(), key=lambda i: i.published_at, reverse=True
        )
        items = list(chunks(market_items, 6))
        buttons = []

        try:
            for item in items[index]:
                buttons.append(
                    InlineKeyboardButton(
                        f"{item.quantity} {get_item_emoji(item.name)} — {item.price} {get_item_emoji('бабло')}",
                        callback_data=f"market_item_open {item._id} {user.id}",
                    )
                )
        except IndexError:
            pass

        markup = InlineKeyboardMarkup(row_width=1)
        buttons.reverse()
        markup.add(*buttons)
        pager_controllers = get_pager_controllers("market", pos=index, user_id=user.id)
        pager_controllers.insert(
            2, InlineKeyboardButton("🛍", callback_data=f"open market-profile {user.id}")
        )
        markup.row(*pager_controllers)

        return markup

    @classmethod
    def market_profile(cls, user: UserModel) -> InlineKeyboardMarkup:
        return quick_markup(
            {
                "👀": {"callback_data": f"market view-my-items {user.id}"},
                "➕": {"callback_data": f"market add {user.id}"},
                "◀️": {"callback_data": f"market start 0 {user.id}"},
            }
        )

    @classmethod
    def market_item_open(
        cls, user: UserModel, market_item: MarketItemModel
    ) -> InlineKeyboardMarkup:
        return quick_markup(
            {
                f"Купить за {market_item.price} {get_item_emoji('бабло')}": {
                    "callback_data": f"market buy {market_item._id} {user.id}"
                },
                "◀️": {"callback_data": f"market start 0 {user.id}"},
            },
            row_width=1,
        )

    @classmethod
    def market_view_my_items(cls, user: UserModel) -> InlineKeyboardMarkup:
        market_items = database.market_items.get_all(owner=user._id)
        buttons = []
        try:
            for item in market_items:
                buttons.append(
                    InlineKeyboardButton(
                        f"{item.quantity} {get_item_emoji(item.name)} — {item.price} {get_item_emoji('бабло')}",
                        callback_data=f"market delete {item._id} {user.id}",
                    )
                )
        except IndexError:
            pass

        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(*buttons)
        markup.row(InlineKeyboardButton("◀️", callback_data=f"market start 0 {user.id}"))
        return markup

    @classmethod
    def delate_state(cls, user: UserModel) -> InlineKeyboardMarkup:
        return quick_markup({"Отмена": {"callback_data": f"delate_state {user.id}"}})

    @classmethod
    def profile(cls, user: UserModel) -> InlineKeyboardMarkup:
        markup = InlineKeyboardMarkup(row_width=2)

        markup.add(
            InlineKeyboardButton("🗄️", callback_data=f"open bag {user.id}"),
            InlineKeyboardButton("🎒", callback_data=f"open equipped_items {user.id}"),
        )
        return markup

    @classmethod
    def bag(cls, user: UserModel) -> InlineKeyboardMarkup:
        markup = InlineKeyboardMarkup(row_width=3)

        items = database.items.get_all(owner=user._id)
        buttons = []
        for item in items:
            if item.quantity <= 0:
                continue
            buttons.append(
                InlineKeyboardButton(
                    f"{get_item_emoji(item.name)} {item.quantity}",
                    callback_data=f"nothing {user.id}",
                )
            )

        markup.add(*buttons)
        logger.debug(f"{len(buttons) = }")

        return markup

    @classmethod
    def daily_gift(
        cls, user: UserModel, daily_gift: DailyGiftModel
    ) -> InlineKeyboardMarkup:
        def get_text():
            if daily_gift.is_claimed:
                return f"🕐 {get_time_difference_string(daily_gift.next_claimable_at - utcnow())}"
            return "🔹  Получить"

        return quick_markup(
            {f"{get_text()}": {"callback_data": f"daily_gift claim {user.id}"}}
        )

    @classmethod
    def transfer_usable_items(
        cls, user: UserModel, to_user: UserModel, item_name: str
    ) -> InlineKeyboardMarkup:
        from base.player import get_or_add_user_usable_items

        markup = InlineKeyboardMarkup(row_width=3)
        buttons = []

        items = get_or_add_user_usable_items(user, item_name)
        items = list(filter(lambda i: i.usage > 0 and i.quantity > 0, items))  # type: ignore
        items.sort(key=lambda i: i.usage)  # type: ignore

        for item in items:
            buttons.append(
                InlineKeyboardButton(
                    f"{get_item_emoji(item.name)} ({item.usage}%)",
                    callback_data=f"transfer {item._id} {to_user.id} {user.id}",
                )
            )

        markup.add(*buttons)
        return markup

    @classmethod
    def achievements_view(
        cls,
        user: UserModel,
        status: Literal["all", "in_progress", "completed", "not_started"] = "all",
    ) -> InlineKeyboardMarkup:
        markup = InlineKeyboardMarkup(row_width=1)
        buttons = []

        achievements = deepcopy(ACHIEVEMENTS)
        if status == "in_progress":
            achievements = [a for a in achievements if achievement_status(user, a) == 0]
        elif status == "not_started":
            achievements = [a for a in achievements if achievement_status(user, a) == 1]
        elif status == "completed":
            achievements = [a for a in achievements if achievement_status(user, a) == 2]

        else:
            achievements.sort(key=lambda a: achievement_status(user, a))

        for achievement in achievements:
            progress = user.achievement_progress.get(achievement.key, 0)
            is_completed = is_completed_achievement(user, achievement.name)
            emoji = ""

            if status == "all":
                if progress > 0 and not is_completed:
                    emoji = "⏳"
                elif is_completed:
                    emoji = "✅"
                else:
                    emoji = "❌"

            buttons.append(
                InlineKeyboardButton(
                    text=f"{emoji} {achievement.name} {achievement.emoji}",
                    callback_data=f"achievements view {achievement.translit()} {user.id}",
                )
            )

        markup.add(*buttons)
        markup.row(
            InlineKeyboardButton("Назад", callback_data=f"achievements main {user.id}")
        )

        return markup

    @classmethod
    def achievements(cls, user: UserModel) -> InlineKeyboardMarkup:
        return quick_markup(
            {
                "Все достижения": {
                    "callback_data": f"achievements filter all {user.id}"
                },
                "В прогрессе": {
                    "callback_data": f"achievements filter in_progress {user.id}"
                },
                "Не начатие": {
                    "callback_data": f"achievements filter not_started {user.id}"
                },
                "Получение": {
                    "callback_data": f"achievements filter completed {user.id}"
                },
            }
        )
