from dataclasses import dataclass
import sys
import json
import logging
from dns import resolver
from typing import Final, List
from datetime import UTC, datetime

import toml
from redis import Redis
from semver import Version

import telebot
from telebot.storage import StateRedisStorage
from telebot.custom_filters import StateFilter, IsDigitFilter


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
    log_chat_id: str
    log_thread_id: int
    owners: List[int]


@dataclass
class WeatherConfig:
    api_key: str
    region: str


@dataclass
class EventConfig:
    start_time: datetime
    end_time: datetime

    def __init__(self, start_time: str, end_time: str, open: bool):
        self.start_time = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        self.end_time = datetime.fromisoformat(end_time.replace("Z", "+00:00"))

    @property
    def open(self) -> bool:
        return self.start_time < datetime.now(UTC) < self.end_time


@dataclass
class ChannelConfig:
    id: str
    chat_id: str


@dataclass
class Config:
    general: GeneralConfig
    database: DatabaseConfig
    redis: RedisConfig
    telegram: TelegramConfig
    weather: WeatherConfig
    event: EventConfig
    channel: ChannelConfig

    @staticmethod
    def from_toml(file_path: str) -> "Config":
        config_data = toml.load(file_path)

        general = GeneralConfig(**config_data.get("general", {}))
        database = DatabaseConfig(**config_data.get("database", {}))
        redis = RedisConfig(**config_data.get("redis", {}))
        telegram = TelegramConfig(**config_data.get("telegram", {}))
        weather = WeatherConfig(**config_data.get("weather", {}))
        event = EventConfig(**config_data.get("event", {}))
        channel = ChannelConfig(**config_data.get("channel", {}))

        return Config(
            general=general,
            database=database,
            redis=redis,
            telegram=telegram,
            weather=weather,
            event=event,
            channel=channel,
        )


config = Config.from_toml("config.toml")


# NOTE: Это для termux
resolver.default_resolver = resolver.Resolver(configure=False)
resolver.default_resolver.nameservers = ["8.8.8.8"]


with open("version") as f:
    version: Final = Version.parse(f.read())

DEBUG = config.general.debug
TOKEN = config.telegram.token
DB_URL = config.database.url
REDIS_URL = config.redis.url
DB_NAME = config.database.name
OPENWEATHER_API_KEY = config.weather.api_key

if not TOKEN:
    raise ValueError("BOT_TOKEN is missing")
elif not DB_URL:
    raise ValueError("DB_URL is missing")
elif not DB_NAME:
    raise ValueError("DB_NAME is missing")
elif not OPENWEATHER_API_KEY:
    raise ValueError("OPENWEATHER_API_KEY is missing")


class RedisStorage(StateRedisStorage):
    def set_record(self, key, value):
        connection = Redis(connection_pool=self.redis)
        connection.setex(self.prefix + str(key), 120, json.dumps(value))
        connection.close()
        return True


state_storage = RedisStorage(redis_url=REDIS_URL)

bot = telebot.TeleBot(
    TOKEN,
    parse_mode="html",
    skip_pending=True,
    num_threads=10,
    disable_web_page_preview=True,
    use_class_middlewares=True,
    state_storage=state_storage,
)

bot.add_custom_filter(StateFilter(bot))
bot.add_custom_filter(IsDigitFilter())

TELEGRAM_ID: Final = 777000
log_chat_id = config.telegram.log_chat_id
log_thread_id = config.telegram.log_thread_id

weather_region: Final = config.weather.region
event_end_time = config.event.end_time
event_open: Final = config.event.open

channel_id: Final = config.channel.id
chat_id: Final = config.channel.chat_id

bot_owners: List[int] = config.telegram.owners

logger = logging.Logger("Bot")


class TelegramLogsHandler(logging.Handler):
    def __init__(self):
        super().__init__()

    def emit(self, record):
        if record.levelno == 10 and record.name == telebot.logger.name:
            return
        from helpers.utils import log

        log_entry = self.format(record)
        log(log_entry, record.levelname, record)
        del log


logger.addHandler(TelegramLogsHandler())
console_output_handler = logging.StreamHandler(sys.stderr)
console_output_handler.setFormatter(telebot.formatter)
logger.addHandler(console_output_handler)

telebot.logger.addHandler(TelegramLogsHandler())
telebot.logger.setLevel(20)
