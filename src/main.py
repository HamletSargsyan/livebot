import argparse
import asyncio

from aiogram import Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import BotCommand
from tinylogging import Level

from config import aiogram_logger, bot, config, logger
from database.funcs import database
from handlers import router as handlers_router
from helpers.exceptions import NoResult
from middlewares import middlewares
from tasks import run_tasks

dp = Dispatcher(
    state_storage=RedisStorage.from_url(config.redis.url),
)

dp.include_router(handlers_router)


async def configure_bot_commands():
    commands = [
        BotCommand(command="profile", description="Профиль"),
        BotCommand(command="daily_gift", description="Ежедневный подарок"),
        BotCommand(command="home", description="Дом"),
        BotCommand(command="bag", description="Инвентарь"),
        BotCommand(command="quest", description="Квест"),
        BotCommand(command="craft", description="Верстак"),
        BotCommand(command="market", description="Рынок"),
        BotCommand(command="use", description="Юз предметов"),
        BotCommand(command="exchanger", description="Обменник"),
        BotCommand(command="transfer", description="Перекидка предметов"),
        BotCommand(command="shop", description="Магазин"),
        BotCommand(command="achievements", description="Достижения"),
        BotCommand(command="weather", description="Погода"),
        BotCommand(command="items", description="Информация о всех приметах"),
        BotCommand(command="casino", description="Казино"),
        BotCommand(command="top", description="Топ"),
        BotCommand(command="ref", description="Реферальная система"),
        BotCommand(command="stats", description="Статистика"),
        BotCommand(command="help", description="Помощь"),
    ]

    if config.event.open:
        commands.insert(0, BotCommand(command="event", description="Ивент"))
        commands.insert(1, BotCommand(command="event_shop", description="Ивентовый магазин"))

    await bot.set_my_commands(commands)


def init_middlewares():
    for middleware in middlewares:
        dp.message.middleware(middleware())


async def main(args: argparse.Namespace):
    logger.info("Бот включен")

    if args.debug:
        config.general.debug = True
        logger.level = Level.DEBUG
        aiogram_logger.setLevel(10)
        logger.warning("Бот работает в режиме DEBUG")

    await configure_bot_commands()
    init_middlewares()

    for uid in config.telegram.owners:
        try:
            user = await database.users.async_get(id=uid)
        except NoResult:
            continue
        user.is_admin = True
        await database.users.async_update(**user.to_dict())

    if not args.without_tasks:
        run_tasks()

    await dp.start_polling(bot, handle_signals=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Запуск телеграм-бота.")
    parser.add_argument("--debug", action="store_true", help="Запуск в режиме отладки")
    parser.add_argument("--without-tasks", action="store_true", help="Запуск без задач")

    args = parser.parse_args()

    asyncio.run(main(args))
