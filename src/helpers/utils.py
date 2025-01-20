import sys
import itertools
import asyncio
import json
import random
import statistics
from contextlib import suppress
from dataclasses import is_dataclass, astuple
from datetime import UTC, datetime, timedelta
from functools import wraps
from typing import (
    Any,
    Iterable,
    Awaitable,
    Callable,
    Generator,
    NoReturn,
    Optional,
    ParamSpec,
    Self,
    TypeVar,
    Union,
)

import httpx
from aiogram.exceptions import TelegramAPIError, TelegramRetryAfter
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from semver import Version

from base.achievements import ACHIEVEMENTS
from base.items import ITEMS
from config import VERSION, bot, config, logger
from database.funcs import cache
from database.models import AchievementModel, UserModel
from helpers.consts import PAGER_CONTROLLERS
from helpers.datatypes import Achievement, Item
from helpers.enums import ItemRarity
from helpers.exceptions import AchievementNotFoundError, ItemNotFoundError, NoResult

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
            msg = (
                f"начиная с версии {deprecated_in} функция `{func.__name__}` помечена"
                f" как устаревшая и будет удалена в версии {remove_in} (текущая версия: {VERSION})"
            )

            if message:
                msg += f" | {message}"

            logger.warning(msg)
            return func(*args, **kwargs)

        return wrapper

    return decorator


def make_hashable(value: Any):
    if isinstance(value, dict):
        return tuple((k, make_hashable(v)) for k, v in sorted(value.items()))
    if isinstance(value, (list, set, tuple)):
        return tuple(make_hashable(v) for v in value)
    if is_dataclass(value):
        return make_hashable(astuple(value))
    return value


def cached(func: Callable[P, T]):
    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        key = frozenset((make_hashable(args), make_hashable(kwargs)))
        if key in cache:
            result: T = cache[key]
        else:
            result = func(*args, **kwargs)
        return result

    return wrapper


def utcnow() -> datetime:
    return datetime.now(UTC)


@cached
def split_string(text: str, chars_per_string: int) -> list[str]:
    return [text[i : i + chars_per_string] for i in range(0, len(text), chars_per_string)]


@cached
def remove_not_allowed_symbols(text: str) -> str:
    not_allowed_symbols = ["#", "<", ">", "{", "}", '"', "'", "$", "(", ")", "@"]
    cleaned_text = "".join(char for char in text if char not in not_allowed_symbols)

    return cleaned_text


@cached
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


@cached
def get_user_tag(user: UserModel):
    return f"<a href='tg://user?id={user.id}'>{user.name}</a>"


@cached
def get_item(name: str) -> Union[Item, NoReturn]:
    for item in ITEMS:
        item.name = item.name.lower()
        if item.name == name:
            return item
        if item.altnames and name in item.altnames:
            return item
        if name == item.translit():
            return item
    raise ItemNotFoundError(f"Item {name} not found")


@cached
def get_item_emoji(item_name: str) -> str:
    try:
        return get_item(item_name).emoji or ""
    except AttributeError:
        return ""


@cached
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
        self.loading_message: Message

    async def __aenter__(self):
        with open("src/base/hints.json") as f:
            hints: list[dict[str, str]] = json.load(f)

        hint = random.choice(hints)

        if "url" in hint:
            markup = quick_markup({"Тык": {"url": hint["url"]}})
        else:
            markup = None

        mess = f"<b>Загрузка...</b>\n\n<i>{hint['message']}</i>"

        try:
            msg = await self.loading_message.reply(mess, reply_markup=markup)
        except Exception:
            msg = await self.message.answer(mess, reply_markup=markup)
        self.loading_message = msg

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self.loading_message.delete()


@cached
def get_pager_controllers(name: str, pos: int, user_id: Union[int, str]):
    return [
        InlineKeyboardButton(
            text=controller.text,
            callback_data=controller.callback_data.format(name=name, pos=pos, user_id=user_id),
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


@cached
def calc_xp_for_level(level: int) -> int:
    return 5 * level + 50 * level + 100


async def check_user_subscription(user: UserModel) -> bool:
    tg_user = await bot.get_chat_member(config.telegram.channel_id, user.id)
    if tg_user.status in ["member", "administrator", "creator"]:
        return True
    return False


async def send_channel_subscribe_message(message: Message):
    chat_info = await message.bot.get_chat(config.telegram.channel_id)
    markup = quick_markup({"Подписаться": {"url": f"t.me/{chat_info.username}"}})
    mess = "Чтобы использовать эту функцию нужно подписаться на новостной канал"
    await message.reply(mess, reply_markup=markup)


def check_version() -> str:  # type: ignore
    url = "https://api.github.com/repos/HamletSargsyan/livebot/releases/latest"

    if "bot_latest_version" in cache:
        version: Version = Version.parse(cache.get("bot_latest_version"))  # type: ignore
    else:
        response = httpx.get(url)

        if response.status_code != 200:
            logger.error(response.text)
            response.raise_for_status()

        latest_release = response.json()
        version = Version.parse(latest_release["tag_name"].replace("v", ""))
        cache["bot_latest_version"] = str(version)

    latest_version = version

    match VERSION.compare(latest_version):
        case -1:
            return "требуется обновление"
        case 0:
            return "актуальная версия"
        case 1:
            return "текущая версия бота больше чем в репозитории"


@cached
def get_achievement(name: str) -> Achievement:
    for achievement in ACHIEVEMENTS:
        if name == achievement.name:
            return achievement
        if name == achievement.translit() or name == achievement.key:
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


async def award_user_achievement(user: UserModel, achievement: Achievement):
    if is_completed_achievement(user, achievement.name):
        return
    from base.player import get_or_add_user_item
    from database.funcs import database

    ach = AchievementModel(name=achievement.name, owner=user._id)
    await database.achievements.async_add(**ach.to_dict())

    reward = ""

    for item, quantity in achievement.reward.items():
        reward = f"+ {quantity} {item} {get_item_emoji(item)}\n"
        if item == "бабло":
            user.coin += quantity
            await database.users.async_update(**user.to_dict())
        else:
            user_item = get_or_add_user_item(user, item)
            user_item.quantity += quantity
            await database.items.async_update(**user_item.to_dict())

    await bot.send_message(
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


@cached
def calc_percentage(part: int, total: int = 100) -> float:
    if total == 0:
        raise ValueError("Общий объем не может быть равен нулю")
    return (part / total) * 100


@cached
def create_progress_bar(percentage: float) -> str:
    if not (0 <= percentage <= 100):  # pylint: disable=superfluous-parens
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
    if is_completed:
        return 2  # Выполнено
    return 1  # Не начато


@cached
def parse_time_duration(time_str: str) -> timedelta:
    """
    Parse time duration in the format like 2d, 3h, 15m and return the timedelta.
    """
    value = int(time_str[:-1])
    unit = time_str[-1]

    if unit == "d":
        return timedelta(days=value)
    if unit == "h":
        return timedelta(hours=value)
    if unit == "m":
        return timedelta(minutes=value)

    raise ValueError("Неверный формат времени. Используйте {d,h,m} для дней, часов, минут.")


@cached
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

    async def __aenter__(self) -> Self:
        self.message = await antiflood(self.user_message.reply(self._mess))

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        for func in self.exit_funcs:
            func()

    async def write(self, new_text: str):
        self._mess = text = f"{self._mess}\n<b>*</b>  {new_text}"
        self.message = await antiflood(self.message.edit_text(text))


async def safe(func: Awaitable[T]) -> Optional[T]:
    with suppress(TelegramAPIError):
        return await antiflood(func)


@cached
def quick_markup(values: dict[str, dict[str, Any]], row_width: int = 2) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    buttons = [InlineKeyboardButton(text=text, **kwargs) for text, kwargs in values.items()]
    builder.add(*buttons)
    builder.adjust(row_width)
    return builder.as_markup()


async def antiflood(func: Awaitable[T]) -> T:
    number_retries = 5
    for _ in range(number_retries):
        try:
            return await func
        except TelegramRetryAfter as e:
            await asyncio.sleep(e.retry_after)
    return await func


if sys.version_info >= (3, 12):
    batched = itertools.batched  # pylint: disable=invalid-name,no-member
else:

    def batched(iterable: Iterable[T], n: int) -> Generator[tuple[T, ...], None, None]:
        # https://docs.python.org/3.12/library/itertools.html#itertools.batched
        if n < 1:
            raise ValueError("n must be at least one")
        iterator = iter(iterable)
        while batch := tuple(itertools.islice(iterator, n)):
            yield batch
