from telebot.types import Message, ChatPermissions
from telebot.util import quick_markup

from database.funcs import database
from database.models import UserModel, Violation
from helpers.utils import get_user_tag, only_admin, parse_time_duration, utcnow
from config import bot


@bot.message_handler(commands=["warn"])
@only_admin
def warn_cmd(message: Message, user: UserModel):
    """
    Usage:
        /warn reason
    """
    if not message.reply_to_message:
        return
    reply_user = database.users.get(id=message.reply_to_message.from_user.id)
    reason = " ".join(message.text.strip().split(" ")[1:])

    if not reason:
        return

    reply_user.violations.append(Violation(reason, "warn"))

    database.users.update(**user.to_dict())

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
@only_admin
def mute_cmd(message: Message, user: UserModel):
    """
    Usage:
        /mute time{d,h,m} [reason]
    """
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
            can_send_messages=False,
        ),
    )

    mess = (
        f"{get_user_tag(reply_user)} получил мут до {mute_end_time!s} по UTC.\n\n"
        f"<b>Причина</b>\n"
        f"<i>{reason}</i>"
    )
    markup = quick_markup(
        {"Правила": {"url": "https://hamletsargsyan.github.io/livebot/rules"}}
    )

    bot.send_message(message.chat.id, mess, reply_markup=markup)
