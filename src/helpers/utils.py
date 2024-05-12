import logging
from datetime import datetime, timedelta
import random
from typing import NoReturn, Union

from telebot.types import Message, ReplyParameters, InlineKeyboardButton
from telebot.util import antiflood, escape, split_string

from config import bot, logger, timezone, log_chat_id, log_thread_id
from database.models import UserModel
from helpers.datatypes import Item
from helpers.exceptions import ItemNotFoundError
from base.items import items_list
from helpers.enums import ItemRarity


def log(log_text: str, log_level: str, record: logging.LogRecord) -> None:
    emoji_dict = {
        "debug": "👾",
        "info": "ℹ️",
        "warn": "⚠️",
        "warning": "⚠️",
        "error": "🛑",
        "critical": "⛔",
    }
    current_time = datetime.now(timezone).strftime("%d.%m.%Y %H:%M:%S")
    log_template = (
        f'<b>{emoji_dict.get(log_level.lower(), "")} {log_level.upper()}</b>\n\n'
        f"{current_time}\n\n"
        f"<b>Логгер:</b> <code>{record.name}</code>\n"
        #    f"<b>Модуль:</b> <code>{record.module}</code>\n"
        f"<b>Путь к файлу:</b> <code>{record.pathname}</code>\n"
        f"<b>Файл</b>: <code>{record.filename}</code>\n"
        f"<b>Строка:</b> {record.lineno}\n\n"
        '<pre><code class="language-shell">{text}</code></pre>'
    )

    for text in split_string(log_text, 3000):
        try:
            antiflood(
                bot.send_message,
                log_chat_id,
                log_template.format(text=escape(text)),
                message_thread_id=log_thread_id,
            )
        except Exception as e:
            logger.exception(e)
            logger.log(record.levelno, text)


def remove_not_allowed_symbols(text: str) -> str:
    if not isinstance(text, str):
        raise TypeError(f"Input text must be a string, not {type(text)}.")

    not_allowed_symbols = ["#", "<", ">", "{", "}", '"', "'", "$", "(", ")", "@"]
    cleaned_text = "".join(char for char in text if char not in not_allowed_symbols)

    return cleaned_text


def get_time_difference_string(d: timedelta) -> str:
    days = d.days
    years, days_in_year = divmod(days, 365)
    months, days_in_month = divmod(days_in_year, 30)
    hours, remainder = divmod(d.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    data = ""
    if years > 0:
        data += f"{years} г. "
    if months > 0:
        data += f"{months} мес. "
    if days_in_month > 0:
        data += f"{days_in_month} д. "
    if hours > 0:
        data += f"{hours} ч. "
    if minutes > 0:
        data += f"{minutes} м. "
    data += f"{seconds} с. "
    return data


def get_user_tag(user: UserModel):
    return f"<a href='tg://user?id={user.id}'>{user.name}</a>"


def get_item(name: str) -> Union[Item, NoReturn]:
    for item in items_list:
        item.name = item.name.lower()
        if item.name == name:
            return item
        elif item.altnames and name in item.altnames:
            return item
        elif name == item.translit():
            return item
    raise ItemNotFoundError(f"Item {name} not found")


def get_item_emoji(item_name: str) -> Union[str, None]:
    try:
        return get_item(item_name).emoji or ""
    except AttributeError:
        return ""


def get_item_count_for_rarity(rarity: ItemRarity) -> int:
    if rarity == ItemRarity.COMMON:
        quantity = random.randint(5, 20)
    elif rarity == ItemRarity.UNCOMMON:
        quantity = random.randint(3, 5)
    elif rarity == ItemRarity.RARE:
        quantity = random.randint(1, 2)
    elif rarity == ItemRarity.EPIC:
        quantity = random.randint(0, 2)
    else:
        quantity = random.randint(0, 1)
    return quantity


class Loading:
    def __init__(self, message: Message):
        self.message = message

    def __enter__(self):
        sitcker_id = (
            "CAACAgEAAxkBAAEpskNl2JfOUfS1vL2nDBb_rqz40YJKsAACjQQAApbcoUZgQGLo1I2DijQE"
        )

        try:
            msg = bot.send_sticker(
                self.message.chat.id,
                sitcker_id,
                reply_parameters=ReplyParameters(self.message.id),
            )
        except Exception:
            msg = bot.send_sticker(self.message.chat.id, sitcker_id)
        self.loading_message = msg

    def __exit__(self, exc_type, exc_value, traceback):
        bot.delete_message(self.loading_message.chat.id, self.loading_message.id)


PAGER_CONTROLLERS = [
    InlineKeyboardButton("↩️", callback_data="{name} start {pos} {user_id}"),
    InlineKeyboardButton("⬅️", callback_data="{name} back {pos} {user_id}"),
    InlineKeyboardButton("➡️", callback_data="{name} next {pos} {user_id}"),
    InlineKeyboardButton("↪️", callback_data="{name} end {pos} {user_id}"),
]


def get_pager_controllers(name: str, pos: int, user_id: Union[int, str]):
    return [
        InlineKeyboardButton(
            controller.text,
            callback_data=controller.callback_data.format(
                name=name, pos=pos, user_id=user_id
            ),
        )
        for controller in PAGER_CONTROLLERS
    ]

def get_middle_item_price(name: str):
    from database.funcs import database
    item = get_item(name)
    market_items = database.market_items.get_all(name=item.name)

    price = 0
    if item.price:
        price += item.price

    for market_item in market_items:
        price
