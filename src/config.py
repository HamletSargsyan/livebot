import json
from dns import resolver
from dataclasses import dataclass
from typing import Final, Optional
from datetime import UTC, datetime

import toml
from redis import Redis
from semver import Version

from tinylogging import Logger, Level, BaseHandler, LoggingAdapterHandler

import telebot
from telebot import ExceptionHandler
from telebot.storage import StateRedisStorage
from telebot.custom_filters import StateFilter, IsDigitFilter


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
    api_key: str
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
        if record.level <= Level.DEBUG and record.name == telebot.logger.name:
            return
        from helpers.utils import log

        log(record)


logger.handlers.add(TelegramLogsHandler())


telebot.logger.handlers = []

for handler in logger.handlers:
    telebot.logger.addHandler(LoggingAdapterHandler(handler))

telebot.logger.setLevel("DEBUG" if config.general.debug else "INFO")


class RedisStorage(StateRedisStorage):
    def set_record(self, key, value):
        connection = Redis(connection_pool=self.redis)
        connection.setex(self.prefix + str(key), 120, json.dumps(value))
        connection.close()
        return True


state_storage = RedisStorage(redis_url=config.redis.url)


class ErrorHandler(ExceptionHandler):
    def handle(self, exception: Exception) -> bool:  # pyright: ignore
        logger.error(str(exception))
        return True


bot = telebot.TeleBot(
    config.telegram.token,
    parse_mode="html",
    skip_pending=True,
    num_threads=10,
    disable_web_page_preview=True,
    use_class_middlewares=True,
    state_storage=state_storage,
    exception_handler=ErrorHandler(),
)


bot.add_custom_filter(StateFilter(bot))
bot.add_custom_filter(IsDigitFilter())
