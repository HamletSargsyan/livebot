from livebot.cli import ARGS  # isort: skip # pylint: disable=C0412
import asyncio
from argparse import Namespace

from aiogram import Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage, SimpleEventIsolation
from aiogram.types import BotCommand

from livebot.config import bot, config, logger
from livebot.consts import APP_NAME, CACHE_DIR, CONFIG_FILE, DATA_DIR, VERSION
from livebot.database.models import UserModel
from livebot.handlers import router
from livebot.helpers.exceptions import NoResult
from livebot.middlewares import middlewares
from livebot.tasks import run_tasks


dp = Dispatcher(
    state_storage=MemoryStorage(),
    events_isolation=SimpleEventIsolation(),
)
dp.include_router(router)


def init_middlewares():
    logger.debug("initializing middlewares")
    for middleware in middlewares:
        dp.message.middleware(middleware())


async def init_bot_commands():
    commands = [
        BotCommand(command="profile", description="Профиль"),
        BotCommand(command="daily_gift", description="Ежедневный подарок"),
        BotCommand(command="home", description="Дом"),
        BotCommand(command="inventory", description="Инвентарь"),
        BotCommand(command="quest", description="Квест"),
        BotCommand(command="craft", description="Верстак"),
        BotCommand(command="market", description="Рынок"),
        BotCommand(command="use", description="Юз предметов"),
        BotCommand(command="transfer", description="Перекидка предметов"),
        BotCommand(command="shop", description="Магазин"),
        BotCommand(command="achievements", description="Достижения"),
        BotCommand(command="weather", description="Погода"),
        BotCommand(command="casino", description="Казино"),
        BotCommand(command="ref", description="Реферальная система"),
        BotCommand(command="help", description="Помощь"),
    ]

    await bot.set_my_commands(commands)


async def init_bot_admins():
    for uid in config.general.owners:
        try:
            user = await UserModel.get_async(id=uid)
        except NoResult:
            continue

        user.is_admin = True
        await user.update_async()


async def main(args: Namespace) -> None:
    logger.info(f"Running {APP_NAME} version {VERSION}")

    if config.general.debug:
        logger.warning("bot running in debug mode")

    logger.debug(f"config file: {CONFIG_FILE}")
    logger.debug(f"data dir: {DATA_DIR}")
    logger.debug(f"cache dir: {CACHE_DIR}")

    for handler in logger.handlers:
        handler.level = logger.level

    await init_bot_admins()
    await init_bot_commands()
    init_middlewares()

    if not args.without_tasks:
        run_tasks()

    await dp.start_polling(bot, handle_signals=False)


def cli_run():
    try:
        asyncio.run(main(ARGS))
    except KeyboardInterrupt:
        logger.info("bot stopped")


if __name__ == "__main__":
    cli_run()
