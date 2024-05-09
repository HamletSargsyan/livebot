import logging
from datetime import datetime, timedelta

from telebot.util import antiflood, escape, split_string

from config import bot, logger, timezone, log_chat_id, log_thread_id
from database.models import UserModel


def log(log_text: str, log_level: str, record: logging.LogRecord) -> None:
    emoji_dict = {
        "debug": "👾",
        "info": "ℹ️",
        "warn": "⚠️",
        "warning": "⚠️",
        "error": "🛑",
        "critical": "⛔",
    }
    current_time = datetime.now(timezone).strftime("%d.%m.%Y %H:%M:%S")
    log_template = (
        f'<b>{emoji_dict.get(log_level.lower(), "")} {log_level.upper()}</b>\n\n'
        f"{current_time}\n\n"
        f"<b>Логгер:</b> <code>{record.name}</code>\n"
        #    f"<b>Модуль:</b> <code>{record.module}</code>\n"
        f"<b>Путь к файлу:</b> <code>{record.pathname}</code>\n"
        f"<b>Файл</b>: <code>{record.filename}</code>\n"
        f"<b>Строка:</b> {record.lineno}\n\n"
        '<pre><code class="language-shell">{text}</code></pre>'
    )

    for text in split_string(log_text, 3000):
        try:
            antiflood(
                bot.send_message,
                log_chat_id,
                log_template.format(text=escape(text)),
                message_thread_id=log_thread_id,
            )
        except Exception as e:
            logger.exception(e)
            logger.log(record.levelno, text)


def remove_not_allowed_symbols(text: str) -> str:
    if not isinstance(text, str):
        raise TypeError(f"Input text must be a string, not {type(text)}.")

    not_allowed_symbols = ["#", "<", ">", "{", "}", '"', "'", "$", "(", ")", "@"]
    cleaned_text = "".join(char for char in text if char not in not_allowed_symbols)

    return cleaned_text


def get_time_difference_string(d: timedelta) -> str:
    days = d.days
    years, days_in_year = divmod(days, 365)
    months, days_in_month = divmod(days_in_year, 30)
    hours, remainder = divmod(d.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    data = ""
    if years > 0:
        data += f"{years} г. "
    if months > 0:
        data += f"{months} мес. "
    if days_in_month > 0:
        data += f"{days_in_month} д. "
    if hours > 0:
        data += f"{hours} ч. "
    if minutes > 0:
        data += f"{minutes} м. "
    data += f"{seconds} с. "
    return data


def get_user_tag(user: UserModel):
    return f"<a href='tg://user?id={user.id}'>{user.name}</a>"
