from contextlib import suppress
from functools import wraps
import json
import random
import statistics
from typing import (
    Any,
    Callable,
    NoReturn,
    Optional,
    ParamSpec,
    Self,
    TypeVar,
    Union,
)
from datetime import UTC, datetime, timedelta

import httpx
from semver import Version

from telebot.types import Message, InlineKeyboardButton, User
from telebot.util import antiflood, escape, split_string, quick_markup

from tinylogging import Record, Level

from base.achievements import ACHIEVEMENTS
from config import (
    bot,
    logger,
    config,
    VERSION,
)
from database.models import AchievementModel, UserModel
from helpers.datatypes import Achievement, Item
from helpers.exceptions import AchievementNotFoundError, ItemNotFoundError, NoResult
from base.items import ITEMS
from helpers.enums import ItemRarity

T = TypeVar("T")
P = ParamSpec("P")

_deprecated_funcs = set()


def deprecated(
    *,
    remove_in: Version,
    deprecated_in: Version,
    message: Optional[str] = None,
    warn_once: bool = True,
):
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            if warn_once and func.__name__ in _deprecated_funcs:
                return func(*args, **kwargs)
            _deprecated_funcs.add(func.__name__)
            msg = f"начиная с версии {deprecated_in} функция `{func.__name__}` помечена как устаревшая и будет удалена в версии {remove_in}, (текущая версия: {VERSION})"

            if message:
                msg += f" | {message}"

            logger.warning(msg)
            return func(*args, **kwargs)

        return wrapper

    return decorator


def utcnow() -> datetime:
    return datetime.now(UTC)


def log(record: Record) -> None:
    emoji_dict = {
        Level.DEBUG: "👾",
        Level.INFO: "ℹ️",
        Level.WARNING: "⚠️",
        Level.ERROR: "🛑",
        Level.CRITICAL: "⛔",
    }
    current_time = datetime.now(UTC).strftime("%d.%m.%Y %H:%M:%S")
    log_template = (
        f'<b>{emoji_dict.get(record.level, "")} {record.level.name}</b>\n\n'
        f"{current_time}\n\n"
        f"<b>Логгер:</b> <code>{record.name}</code>\n"  # cspell: disable-line
        # f"<b>Модуль:</b> <code>{record.module}</code>\n"
        f"<b>Путь к файлу:</b> <code>{record.filename}</code>\n"
        f"<b>Файл</b>: <code>{record.relpath}</code>\n"
        f"<b>Строка:</b> {record.line}\n\n"
        '<pre><code class="language-shell">{text}</code></pre>'
    )

    for text in split_string(record.message, 3000):
        try:
            antiflood(
                bot.send_message,
                config.telegram.log_chat_id,
                log_template.format(text=escape(text)),
                message_thread_id=config.telegram.log_thread_id,
            )
        except Exception as e:
            print(e)
            print(text)


def remove_not_allowed_symbols(text: str) -> str:
    not_allowed_symbols = ["#", "<", ">", "{", "}", '"', "'", "$", "(", ")", "@"]
    cleaned_text = "".join(char for char in text if char not in not_allowed_symbols)

    return cleaned_text


def get_time_difference_string(d: timedelta) -> str:
    years, days_in_year = divmod(d.days, 365)
    months, days = divmod(days_in_year, 30)
    hours, remainder = divmod(d.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    data = ""
    if years > 0:
        data += f"{years} г. "
    if months > 0:
        data += f"{months} мес. "
    if days > 0:
        data += f"{days} д. "
    if hours > 0:
        data += f"{hours} ч. "
    if minutes > 0:
        data += f"{minutes} м. "

    data += f"{seconds} с. "
    return data


def get_user_tag(user: UserModel):
    return f"<a href='tg://user?id={user.id}'>{user.name}</a>"


def get_item(name: str) -> Union[Item, NoReturn]:
    for item in ITEMS:
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
        with open("src/base/hints.json") as f:
            hints: list[dict[str, str]] = json.load(f)

        hint = random.choice(hints)

        if "url" in hint:
            markup = quick_markup({"Тык": {"url": hint["url"]}})
        else:
            markup = None

        mess = f"<b>Загрузка...</b>\n\n<i>{hint['message']}</i>"

        try:
            msg = bot.reply_to(self.message, mess, reply_markup=markup)
        except Exception:
            msg = bot.send_message(self.message.chat.id, mess, reply_markup=markup)
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

    match VERSION.compare(latest_version):
        case -1:
            return "требуется обновление"
        case 0:
            return "актуальная версия"
        case 1:
            return "текущая версия бота больше чем в репозитории"


@deprecated(
    remove_in=Version(major=12),
    deprecated_in=Version(major=10),
    message="Use `message.from_user` instead",
)
def from_user(message: Message) -> User:
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
    percentage = min(100.0, calc_percentage(achievement_progress, ach.need))

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


def parse_time_duration(time_str: str) -> timedelta:
    """
    Parse time duration in the format like 2d, 3h, 15m and return the timedelta.
    """
    value = int(time_str[:-1])
    unit = time_str[-1]

    if unit == "d":
        return timedelta(days=value)
    elif unit == "h":
        return timedelta(hours=value)
    elif unit == "m":
        return timedelta(minutes=value)
    else:
        raise ValueError(
            "Неверный формат времени. Используйте {d,h,m} для дней, часов, минут."
        )


def pretty_datetime(d: datetime) -> str:
    return d.strftime("%H:%M %d.%m.%Y")


class MessageEditor:
    def __init__(
        self,
        user_message: Message,
        *,
        title: str,
    ):
        self.user_message = user_message
        self.message: Message

        self.title = title
        self._mess = f"<b>{self.title}</b>"
        self.exit_funcs: set[Callable[[], None | Any]] = set()

    def __enter__(self) -> Self:
        self.message = antiflood(bot.reply_to, self.user_message, self._mess)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        for func in self.exit_funcs:
            func()

    def write(self, new_text: str):
        self._mess = text = f"{self._mess}\n<b>*</b>  {new_text}"
        self.message = antiflood(
            bot.edit_message_text, text, self.message.chat.id, self.message.id
        )


def safe(func: Callable[P, T], *args: P.args, **kwargs: P.kwargs) -> Optional[T]:
    with suppress(BaseException):
        return func(*args, **kwargs)
