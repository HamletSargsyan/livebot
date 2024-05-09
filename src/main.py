import bot as _  # noqa
from middlewares.register import RegisterMiddleware
from config import bot, DEBUG, logger


def main() -> None:
    logger.info("Бот включён")

    if DEBUG:
        logger.warning("Бот работает в режиме debug")

    bot.setup_middleware(RegisterMiddleware())
    bot.infinity_polling(timeout=500, skip_pending=True)


if __name__ == "__main__":
    main()
