import logging
from typing import Final

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.types import LinkPreviewOptions
from tinylogging import Level, Logger, LoggingAdapterHandler

from livebot.cli import ARGS
from livebot.config_types import Config
from livebot.consts import APP_NAME, CACHE_DIR, CONFIG_DIR, DATA_DIR


for directory in [CONFIG_DIR, CACHE_DIR, DATA_DIR]:
    directory.mkdir(exist_ok=True)

config: Final = Config.from_file(ARGS.config)
config.merge(ARGS)

logger: Final = Logger(APP_NAME, Level.DEBUG if config.general.debug else Level.INFO)

# logger.handlers.add(
#     TelegramHandler(
#         chat_id=config.telegram.log_chat_id,
#         token=config.telegram.token,
#         message_thread_id=config.telegram.log_thread_id,
#         formatter=TelegramFormatter(),
#         ignore_errors=True,
#     )
# )

aiogram_logger = logging.getLogger("aiogram")

if config.general.debug:
    aiogram_logger.setLevel(10)  # debug
else:
    aiogram_logger.setLevel(30)  # warning

aiogram_logger.handlers = []

aiogram_logger.setLevel(logger.level.name.upper())

for handler in logger.handlers:
    aiogram_logger.handlers.append(LoggingAdapterHandler(handler))

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
