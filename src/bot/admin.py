from telebot.types import Message, ChatPermissions
from telebot.util import quick_markup

from database.funcs import database
from database.models import Violation
from helpers.utils import get_user_tag, parse_time_duration, pretty_datetime, utcnow
from config import bot


@bot.message_handler(commands=["warn"])
def warn_cmd(message: Message):
    user = database.users.get(id=message.from_user.id)
    if not user.is_admin:
        return

    bot.reply_to(message, "t")
    if not message.reply_to_message:
        return
    reply_user = database.users.get(id=message.reply_to_message.from_user.id)
    reason = " ".join(message.text.strip().split(" ")[1:])
    if not reason:
        return

    reply_user.violations.append(Violation(reason, "warn"))

    database.users.update(**reply_user.to_dict())

    mess = (
        f"{get_user_tag(reply_user)} получил варн.\n\n"
        f"<b>Причина</b>\n"
        f"<i>{reason}</i>"
    )
    markup = quick_markup(
        {"Правила": {"url": "https://hamletsargsyan.github.io/livebot/rules"}}
    )

    bot.send_message(message.chat.id, mess, reply_markup=markup)


@bot.message_handler(commands=["mute"])
def mute_cmd(message: Message):
    user = database.users.get(id=message.from_user.id)
    if not user.is_admin:
        return

    if not message.reply_to_message:
        return
    reply_user = database.users.get(id=message.reply_to_message.from_user.id)

    args = message.text.strip().split(" ")[1:]

    if not args:
        return

    time_str = args[0]
    reason = " ".join(args[1:]) if len(args) > 1 else "Без причины"

    try:
        mute_duration = parse_time_duration(time_str)
    except ValueError as e:
        bot.send_message(message.chat.id, f"Ошибка: {str(e)}")
        return

    mute_end_time = utcnow() + mute_duration

    reply_user.violations.append(Violation(reason, "mute", until_date=mute_end_time))

    database.users.update(**reply_user.to_dict())

    bot.restrict_chat_member(
        message.chat.id,
        reply_user.id,
        mute_end_time,
        permissions=ChatPermissions(
            can_send_messages=False, can_send_other_messages=False
        ),
    )

    mess = (
        f"{get_user_tag(reply_user)} получил мут до {pretty_datetime(mute_end_time)} по UTC.\n\n"
        f"<b>Причина</b>\n"
        f"<i>{reason}</i>"
    )
    markup = quick_markup(
        {"Правила": {"url": "https://hamletsargsyan.github.io/livebot/rules"}}
    )

    bot.send_message(message.chat.id, mess, reply_markup=markup)


@bot.message_handler(commands=["ban"])
def ban_cmd(message: Message):
    user = database.users.get(id=message.from_user.id)
    if not user.is_admin:
        return

    if not message.reply_to_message:
        return
    reply_user = database.users.get(id=message.reply_to_message.from_user.id)

    args = message.text.strip().split(" ")[1:]

    if not args:
        return

    time_str = args[0]
    reason = " ".join(args[1:]) if len(args) > 1 else "Без причины"

    try:
        ban_duration = parse_time_duration(time_str)
    except ValueError as e:
        bot.send_message(message.chat.id, f"Ошибка: {str(e)}")
        return

    ban_end_time = utcnow() + ban_duration

    reply_user.violations.append(Violation(reason, "ban", until_date=ban_end_time))

    database.users.update(**reply_user.to_dict())

    bot.restrict_chat_member(
        message.chat.id,
        reply_user.id,
        ban_end_time,
        permissions=ChatPermissions(
            can_send_messages=False,
        ),
    )

    bot.ban_chat_member(message.chat.id, reply_user.id, ban_end_time)

    mess = (
        f"{get_user_tag(reply_user)} получил бан до {pretty_datetime(ban_end_time)} по UTC.\n\n"
        f"<b>Причина</b>\n"
        f"<i>{reason}</i>"
    )
    markup = quick_markup(
        {"Правила": {"url": "https://hamletsargsyan.github.io/livebot/rules"}}
    )

    bot.send_message(message.chat.id, mess, reply_markup=markup)


@bot.message_handler(commands=["pban"])
def pban_cmd(message: Message):
    """
    Usage:
        /pban time{d,h,m} [reason]
    """
    user = database.users.get(id=message.from_user.id)
    if not user.is_admin:
        return

    if not message.reply_to_message:
        return
    reply_user = database.users.get(id=message.reply_to_message.from_user.id)

    args = message.text.strip().split(" ")[1:]

    if not args:
        return

    reason = " ".join(args[1:]) if len(args) > 1 else "Без причины"

    reply_user.violations.append(Violation(reason, "permanent-ban"))

    database.users.update(**reply_user.to_dict())

    bot.ban_chat_member(message.chat.id, reply_user.id)

    mess = (
        f"{get_user_tag(reply_user)} получил перманентный бан.\n\n"
        f"<b>Причина</b>\n"
        f"<i>{reason}</i>"
    )
    markup = quick_markup(
        {"Правила": {"url": "https://hamletsargsyan.github.io/livebot/rules"}}
    )

    bot.send_message(message.chat.id, mess, reply_markup=markup)


@bot.message_handler(commands=["unban"])
def unban_cmd(message: Message):
    user = database.users.get(id=message.from_user.id)
    if not user.is_admin:
        return

    if not message.reply_to_message:
        return
    reply_user = database.users.get(id=message.reply_to_message.from_user.id)
    reply_user.violations = [
        violation
        for violation in reply_user.violations
        if violation.type not in ["ban", "permanent-ban"]
    ]
    database.users.update(**reply_user.to_dict())
    bot.unban_chat_member(message.chat.id, reply_user.id, only_if_banned=True)

    bot.send_message(message.chat.id, f"{get_user_tag(reply_user)} разбанен")
