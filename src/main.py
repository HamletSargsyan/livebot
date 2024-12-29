from threading import Thread

import argparse
import telebot
from telebot.types import BotCommand

from tinylogging import Level

import handlers as _  # noqa: F401
from helpers.exceptions import NoResult
from threads.check import check
from threads.notification import notification
from database.funcs import database
from config import bot, config, logger
from middlewares import middlewares


def configure_bot_commands():
    commands = [
        BotCommand("profile", "Профиль"),
        BotCommand("daily_gift", "Ежедневный подарок"),
        BotCommand("home", "Дом"),
        BotCommand("bag", "Инвентарь"),
        BotCommand("quest", "Квест"),
        BotCommand("craft", "Верстак"),
        BotCommand("market", "Рынок"),
        BotCommand("use", "Юз предметов"),
        BotCommand("exchanger", "Обменник"),
        BotCommand("transfer", "Перекидка предметов"),
        BotCommand("shop", "Магазин"),
        BotCommand("achievements", "Достижения"),
        BotCommand("weather", "Погода"),
        BotCommand("items", "Информация о всех приметах"),
        BotCommand("casino", "Казино"),
        BotCommand("top", "Топ"),
        BotCommand("ref", "Реферальная система"),
        BotCommand("stats", "Статистика"),
        BotCommand("help", "Помощь"),
    ]

    if config.event.open:
        commands.insert(0, BotCommand("event", "Ивент"))
        commands.insert(1, BotCommand("event_shop", "Ивентовый магазин"))

    bot.set_my_commands(commands)


def init_middlewares():
    for middleware in middlewares:
        bot.setup_middleware(middleware())


def start_threads():
    threads = [
        Thread(target=check, daemon=True),
        Thread(target=notification, daemon=True),
    ]
    for thread in threads:
        thread.start()


def main(args: argparse.Namespace):
    logger.info("Бот включен")

    if args.debug:
        config.general.debug = True
        logger.level = Level.DEBUG
        telebot.logger.setLevel(10)
        logger.warning("Бот работает в режиме DEBUG")

    configure_bot_commands()
    init_middlewares()

    if not args.without_threads:
        start_threads()

    for uid in config.telegram.owners:
        try:
            user = database.users.get(id=uid)
        except NoResult:
            continue
        user.is_admin = True
        database.users.update(**user.to_dict())

    bot.infinity_polling(timeout=500, skip_pending=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Запуск телеграм-бота.")
    parser.add_argument("--debug", action="store_true", help="Запуск в режиме отладки")
    parser.add_argument("--without-threads", action="store_true", help="Запуск без потоков")

    args = parser.parse_args()

    main(args)
