import logging
from datetime import UTC, datetime, timedelta
import random
import statistics
from typing import Callable, NoReturn, Union
from typing_extensions import deprecated


import httpx
from semver import Version
from telebot.types import Message, ReplyParameters, InlineKeyboardButton, User
from telebot.util import antiflood, escape, split_string, quick_markup

from base.achievements import ACHIEVEMENTS
from config import (
    bot,
    logger,
    config,
    version,
)
from database.models import AchievementModel, UserModel
from helpers.datatypes import Achievement, Item
from helpers.exceptions import AchievementNotFoundError, ItemNotFoundError, NoResult
from base.items import items_list
from helpers.enums import ItemRarity


def utcnow() -> datetime:
    return datetime.now(UTC)


def log(log_text: str, log_level: str, record: logging.LogRecord) -> None:
    emoji_dict = {
        "debug": "👾",
        "info": "ℹ️",
        "warn": "⚠️",
        "warning": "⚠️",
        "error": "🛑",
        "critical": "⛔",
    }
    current_time = utcnow().strftime("%d.%m.%Y %H:%M:%S")
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
                config.telegram.log_chat_id,
                log_template.format(text=escape(text)),
                message_thread_id=config.telegram.log_thread_id,
            )
        except Exception as e:
            logger.exception(e)
            logger.log(record.levelno, text)


def remove_not_allowed_symbols(text: str) -> str:
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


def get_item_emoji(item_name: str) -> str:
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
        sticker_id = "CAACAgEAAxkBAAEpskNl2JfOUfS1vL2nDBb_rqz40YJKsAACjQQAApbcoUZgQGLo1I2DijQE"  # cspell:ignore CAAC, Epsk, YJKs, Apbco

        try:
            msg = bot.send_sticker(
                self.message.chat.id,
                sticker_id,
                reply_parameters=ReplyParameters(self.message.id),
            )
        except Exception:
            msg = bot.send_sticker(self.message.chat.id, sticker_id)
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


def get_middle_item_price(name: str) -> int:
    from database.funcs import database

    item = get_item(name)
    market_items = database.market_items.get_all(name=item.name)

    price = 0
    items = [market_item.price / market_item.quantity for market_item in market_items]
    try:
        if item.price:
            price += statistics.median([item.price, *items])
        else:
            price += statistics.median(items)
    except statistics.StatisticsError:
        pass
    return int(price)


def calc_xp_for_level(level: int) -> int:
    return 5 * level + 50 * level + 100


def check_user_subscription(user: UserModel) -> bool:
    tg_user = bot.get_chat_member(config.telegram.channel_id, user.id)
    if tg_user.status in ["member", "administrator", "creator"]:
        return True
    return False


def send_channel_subscribe_message(message: Message):
    chat_info = bot.get_chat(config.telegram.channel_id)
    markup = quick_markup({"Подписаться": {"url": f"t.me/{chat_info.username}"}})
    mess = "Чтобы использовать эту функцию нужно подписаться на новостной канал"
    bot.reply_to(message, mess, reply_markup=markup)


def check_version() -> str:  # type: ignore
    url = "https://api.github.com/repos/HamletSargsyan/livebot/releases/latest"
    response = httpx.get(url)

    if response.status_code != 200:
        logger.error(response.text)
        response.raise_for_status()

    latest_release = response.json()

    latest_version = Version.parse(latest_release["tag_name"].replace("v", ""))

    match version.compare(latest_version):
        case -1:
            return "требуется обновление"
        case 0:
            return "актуальная версия"
        case 1:
            return "текущая версия бота больше чем в репозитории"


@deprecated("Deprecated. Use `message.from_user` instead", category=DeprecationWarning)
def from_user(message: Message) -> User:
    """
    pyright hack
    """
    return message.from_user  # type: ignore


def get_achievement(name: str) -> Achievement:
    for achievement in ACHIEVEMENTS:
        if name == achievement.name:
            return achievement
        elif name == achievement.translit() or name == achievement.key:
            return achievement
    raise AchievementNotFoundError(name)


def achievement_progress(user: UserModel, name: str) -> str:
    ach = get_achievement(name)
    achievement_progress = user.achievement_progress.get(ach.key, 0)
    percentage = calc_percentage(achievement_progress, ach.need)

    progress = f"Выполнил: {achievement_progress}/{ach.need}\n"
    progress += f"[{create_progress_bar(percentage)}] {percentage:.2f}%"
    return progress


def is_completed_achievement(user: UserModel, name: str) -> bool:
    from database.funcs import database

    try:
        database.achievements.get(owner=user._id, name=name)
        return True
    except NoResult:
        return False


def award_user_achievement(user: UserModel, achievement: Achievement):
    if is_completed_achievement(user, achievement.name):
        return
    from database.funcs import database
    from base.player import get_or_add_user_item

    ach = AchievementModel(name=achievement.name, owner=user._id)
    database.achievements.add(**ach.to_dict())

    reward = ""

    for item, quantity in achievement.reward.items():
        reward = f"+ {quantity} {item} {get_item_emoji(item)}\n"
        if item == "бабло":
            user.coin += quantity
            database.users.update(**user.to_dict())
        else:
            user_item = get_or_add_user_item(user, item)
            user_item.quantity += quantity
            database.items.update(**user_item.to_dict())

    bot.send_message(
        user.id,
        f'Поздравляю🎉, ты получил достижение "{ach.name}"\n\nЗа это ты получил:\n{reward}',
    )


def increment_achievement_progress(user: UserModel, key: str, quantity: int = 1):
    if not is_completed_achievement(user, key.replace("-", " ")):
        from database.funcs import database

        if key in user.achievement_progress:
            user.achievement_progress[key] += quantity
        else:
            user.achievement_progress[key] = quantity

        database.users.update(
            user._id,
            **{f"achievement_progress.{key}": user.achievement_progress[key]},
        )


def calc_percentage(part: int, total: int = 100) -> float:
    if total == 0:
        raise ValueError("Общий объем не может быть равен нулю")
    return (part / total) * 100


def create_progress_bar(percentage: float) -> str:
    if not (0 <= percentage <= 100):
        raise ValueError("Процент должен быть в диапазоне от 0 до 100.")

    length: int = 10
    filled_length = int(length * percentage // 100)
    empty_length = length - filled_length

    filled_block = "■"
    empty_block = "□"

    progress_bar = filled_block * filled_length + empty_block * empty_length
    return progress_bar


def achievement_status(user: UserModel, achievement: Achievement) -> int:
    progress = user.achievement_progress.get(achievement.key, 0)
    is_completed = is_completed_achievement(user, achievement.name)
    if progress > 0 and not is_completed:
        return 0  # В процессе
    elif is_completed:
        return 2  # Выполнено
    else:
        return 1  # Не начато


def only_admin(func: Callable[[Message, UserModel], None]):
    from database.funcs import database

    def wrapper(message: Message):
        user = database.users.get(id=message.from_user.id)
        if user.is_admin or user.id in config.telegram.owners:
            return func(message, user)

    return wrapper
