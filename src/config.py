import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Final, Optional

import toml

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.types import LinkPreviewOptions

from dns import resolver
from semver import Version
from tinylogging import BaseHandler, Level, Logger, LoggingAdapterHandler

TELEGRAM_ID: Final = 777000

# ---------------------------------------------------------------------------- #
#                                 config types                                 #
# ---------------------------------------------------------------------------- #


@dataclass
class GeneralConfig:
    debug: bool = False


@dataclass
class DatabaseConfig:
    url: str
    name: str = "livebot"


@dataclass
class RedisConfig:
    url: str


@dataclass
class TelegramConfig:
    token: str
    owners: list[int]
    channel_id: str
    chat_id: str
    log_chat_id: str
    log_thread_id: Optional[int] = None


@dataclass
class WeatherConfig:
    region: str


@dataclass
class EventConfig:
    start_time: datetime
    end_time: datetime

    def __init__(self, start_time: str, end_time: str):
        self.start_time = datetime.fromisoformat(start_time)
        self.end_time = datetime.fromisoformat(end_time)

    @property
    def open(self) -> bool:
        return self.start_time < datetime.now(UTC) < self.end_time


@dataclass
class Config:
    general: GeneralConfig
    database: DatabaseConfig
    redis: RedisConfig
    telegram: TelegramConfig
    weather: WeatherConfig
    event: EventConfig

    @staticmethod
    def from_toml(file_path: str) -> "Config":
        config_data = toml.load(file_path)

        general = GeneralConfig(**config_data.get("general", {}))
        database = DatabaseConfig(**config_data.get("database", {}))
        redis = RedisConfig(**config_data.get("redis", {}))
        telegram = TelegramConfig(**config_data.get("telegram", {}))
        weather = WeatherConfig(**config_data.get("weather", {}))
        event = EventConfig(**config_data.get("event", {}))

        return Config(
            general=general,
            database=database,
            redis=redis,
            telegram=telegram,
            weather=weather,
            event=event,
        )


# ---------------------------------------------------------------------------- #

config: Final = Config.from_toml("config.toml")

# NOTE: Это для termux
resolver.default_resolver = resolver.Resolver(configure=False)
resolver.default_resolver.nameservers = ["8.8.8.8"]


with open("version") as f:
    VERSION: Final = Version.parse(f.read())


logger = Logger("Bot", Level.DEBUG if config.general.debug else Level.INFO)


class TelegramLogsHandler(BaseHandler):
    def emit(self, record):
        if record.level <= Level.DEBUG and record.name == aiogram_logger.name:
            return
        from helpers.utils import log  # pylint: disable=cyclic-import

        log(record)


logger.handlers.add(TelegramLogsHandler())

aiogram_logger = logging.getLogger("aiogram")
aiogram_logger.handlers = []

for handler in logger.handlers:
    aiogram_logger.handlers.append(LoggingAdapterHandler(handler))

# logging.basicConfig(
#     level=logging.DEBUG,
#     format="%(asctime)s - %(levelname)s - %(module)s - %(message)s",
#     datefmt="%d-%m-%y %H:%M:%S",
# )


bot: Final = Bot(
    token=config.telegram.token,
    default=DefaultBotProperties(
        parse_mode="html",
        allow_sending_without_reply=True,
        link_preview=LinkPreviewOptions(
            is_disabled=True,
        ),
    ),
)


# TODO
# bot.add_custom_filter(StateFilter(bot))
# bot.add_custom_filter(IsDigitFilter())
