import sys
from threading import Thread

from telebot.types import BotCommand

from config import bot, DEBUG, logger, event_open


without_threads = False
if "--debug" in sys.argv:
    from config import telebot

    telebot.logger.setLevel(10)
    DEBUG = True
if "--without-threads" in sys.argv:
    without_threads = True

from middlewares.register import RegisterMiddleware  # noqa: E402

from threads.check import check  # noqa
from threads.notification import notification  # noqa: E402

import bot as _  # noqa


def bot_commands_init():
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


def init_middlewars():
    bot.setup_middleware(RegisterMiddleware())


def init_threads():
    check_thread = Thread(target=check, daemon=True)
    check_thread.start()

    notification_thread = Thread(target=notification, daemon=True)
    notification_thread.start()


def main():
    logger.info("Бот включен")

    if DEBUG:
        logger.warning("Бот работает в режиме DEBUG")

    bot_commands_init()

    if not without_threads:
        init_middlewars()
        init_threads()

    bot.infinity_polling(timeout=500, skip_pending=True)


if __name__ == "__main__":
    main()
