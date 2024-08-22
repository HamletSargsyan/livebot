import os
import sys
import json
import logging
from typing import Final
from datetime import UTC, datetime

from dns import resolver

from redis import Redis
from dotenv import load_dotenv

from semver import Version

import telebot
from telebot.storage import StateRedisStorage
from telebot.custom_filters import StateFilter, IsDigitFilter


load_dotenv()

# NOTE: Это для termux
resolver.default_resolver = resolver.Resolver(configure=False)
resolver.default_resolver.nameservers = ["8.8.8.8"]


with open("version") as f:
    version: Final = Version.parse(f.read())

DEBUG = False

TOKEN = os.getenv("BOT_TOKEN", "")
DB_URL = os.getenv("DB_URL", "")
REDIS_URL = os.getenv("REDIS_URL", "")
DB_NAME = os.getenv("DB_NAME", "livebot")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API", "")

if not TOKEN:
    raise ValueError
elif not DB_URL:
    raise ValueError
elif not DB_NAME:
    raise ValueError
elif not OPENWEATHER_API_KEY:
    raise ValueError


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


log_chat_id = "-1002110527910"
log_thread_id = 2

weather_region: Final = "Сыктывкар"


event_end_time: Final = datetime(2024, 6, 1, 0, 0, 0, tzinfo=UTC)
event_open: Final = False

channel_id: Final = "-1002081230318"
chat_id: Final = "-1001869913117"


bot_owners = [5161392463]  # type: list[int]

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
