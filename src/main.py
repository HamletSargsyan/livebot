from threading import Thread
import argparse

from telebot.types import BotCommand

import bot as _  # noqa: F401
from threads.check import check
from config import DEBUG, bot, event_open, logger
from threads.notification import notification
from middlewares.register import RegisterMiddleware


def configure_bot_commands():
    commands = [
        BotCommand("profile", "Профиль"),
        BotCommand("home", "Дом"),
        BotCommand("bag", "Инвентарь"),
        BotCommand("quest", "Квест"),
        BotCommand("craft", "Верстак"),
        BotCommand("market", "Рынок"),
        BotCommand("use", "Юз придметов"),
        BotCommand("exchanger", "Обменник"),
        BotCommand("transfer", "Перекидка придметов"),
        BotCommand("shop", "Магазин"),
        BotCommand("weather", "Погода"),
        BotCommand("items", "Информация о всех придметах"),
        BotCommand("casino", "Казино"),
        BotCommand("top", "Топ"),
        BotCommand("ref", "Реферальная система"),
        BotCommand("stats", "Статистика"),
        BotCommand("help", "Помощь"),
    ]

    if event_open:
        commands.insert(0, BotCommand("event", "Ивент"))

    bot.set_my_commands(commands)


def init_middlewares():
    bot.setup_middleware(RegisterMiddleware())


def start_threads():
    threads = [
        Thread(target=check, daemon=True),
        Thread(target=notification, daemon=True),
    ]
    for thread in threads:
        thread.start()


def main(args):
    logger.info("Бот включен")

    if args.debug:
        logger.warning("Бот работает в режиме DEBUG")

    configure_bot_commands()

    if not args.without_threads:
        init_middlewares()
        start_threads()

    bot.infinity_polling(timeout=500, skip_pending=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Запуск телеграм-бота.")
    parser.add_argument("--debug", action="store_true", help="Запуск в режиме отладки")
    parser.add_argument(
        "--without-threads", action="store_true", help="Запуск без потоков"
    )

    args = parser.parse_args()

    if args.debug:
        DEBUG = True

    main(args)
