import random
import string
import time
from functools import partial

from aiogram import Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command, CommandObject
from aiogram.types import ChatPermissions, Message

from config import logger
from database.funcs import database, redis_cache
from database.models import PromoModel, Violation
from helpers.exceptions import NoResult
from helpers.utils import (
    Loading,
    MessageEditor,
    antiflood,
    get_item,
    get_user_tag,
    parse_time_duration,
    pretty_datetime,
    quick_markup,
    utcnow,
)

router = Router()


@router.message(Command("warn"))
async def warn_cmd(message: Message, command: CommandObject):
    user = database.users.get(id=message.from_user.id)
    if not user.is_admin:
        return

    if not message.reply_to_message:
        return
    reply_user = database.users.get(id=message.reply_to_message.from_user.id)
    reason = command.args
    if not reason:
        return

    reply_user.violations.append(Violation(reason, "warn"))

    database.users.update(**reply_user.to_dict())

    mess = f"{get_user_tag(reply_user)} получил варн.\n\n<b>Причина</b>\n<i>{reason}</i>"
    markup = quick_markup({"Правила": {"url": "https://hamletsargsyan.github.io/livebot/rules"}})

    await message.answer(mess, reply_markup=markup)


@router.message(Command("mute"))
async def mute_cmd(message: Message, command: CommandObject):
    user = database.users.get(id=message.from_user.id)
    if not user.is_admin:
        return

    if not message.reply_to_message:
        return
    reply_user = database.users.get(id=message.reply_to_message.from_user.id)

    args = command.args
    if args is None:
        return
    args = args.strip().split(" ")
    time_str = args[0]
    reason = " ".join(args[1:]) if len(args) > 1 else "Без причины"

    try:
        mute_duration = parse_time_duration(time_str)
    except ValueError as e:
        await message.reply(f"Ошибка: {str(e)}")
        return

    mute_end_time = utcnow() + mute_duration

    reply_user.violations.append(Violation(reason, "mute", until_date=mute_end_time))

    database.users.update(**reply_user.to_dict())

    await message.bot.restrict_chat_member(
        message.chat.id,
        reply_user.id,
        permissions=ChatPermissions(can_send_messages=False, can_send_other_messages=False),
        until_date=mute_end_time,
    )

    mess = (
        f"{get_user_tag(reply_user)} получил мут до {pretty_datetime(mute_end_time)} по UTC.\n\n"
        f"<b>Причина</b>\n"
        f"<i>{reason}</i>"
    )
    markup = quick_markup({"Правила": {"url": "https://hamletsargsyan.github.io/livebot/rules"}})

    await message.answer(mess, reply_markup=markup)


@router.message(Command("ban"))
async def ban_cmd(message: Message, command: CommandObject):
    user = database.users.get(id=message.from_user.id)
    if not user.is_admin:
        return

    if not message.reply_to_message:
        return
    reply_user = database.users.get(id=message.reply_to_message.from_user.id)

    args = command.args

    if not args:
        return
    args = args.strip().split(" ")

    time_str = args[0]
    reason = " ".join(args[1:]) if len(args) > 1 else "Без причины"

    try:
        ban_duration = parse_time_duration(time_str)
    except ValueError as e:
        await message.reply(f"Ошибка: {str(e)}")
        return

    ban_end_time = utcnow() + ban_duration

    reply_user.violations.append(Violation(reason, "ban", until_date=ban_end_time))

    database.users.update(**reply_user.to_dict())

    await message.bot.restrict_chat_member(
        message.chat.id,
        reply_user.id,
        permissions=ChatPermissions(
            can_send_messages=False,
        ),
        until_date=ban_end_time,
    )

    await message.bot.ban_chat_member(
        message.chat.id,
        reply_user.id,
        until_date=ban_end_time,
    )

    mess = (
        f"{get_user_tag(reply_user)} получил бан до {pretty_datetime(ban_end_time)} по UTC.\n\n"
        f"<b>Причина</b>\n"
        f"<i>{reason}</i>"
    )
    markup = quick_markup({"Правила": {"url": "https://hamletsargsyan.github.io/livebot/rules"}})

    await message.answer(mess, reply_markup=markup)


@router.message(Command("pban"))
async def pban_cmd(message: Message, command: CommandObject):
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

    args = command.args

    if args is None:
        return
    args = args.strip().split()
    reason = " ".join(args[1:]) if len(args) > 1 else "Без причины"

    reply_user.violations.append(Violation(reason, "permanent-ban"))

    database.users.update(**reply_user.to_dict())

    await message.bot.ban_chat_member(message.chat.id, reply_user.id)

    mess = (
        f"{get_user_tag(reply_user)} получил перманентный бан.\n\n<b>Причина</b>\n<i>{reason}</i>"
    )
    markup = quick_markup({"Правила": {"url": "https://hamletsargsyan.github.io/livebot/rules"}})

    await message.answer(mess, reply_markup=markup)


@router.message(Command("unban"))
async def unban_cmd(message: Message):
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
    await message.bot.unban_chat_member(message.chat.id, reply_user.id, only_if_banned=True)

    await message.answer(f"{get_user_tag(reply_user)} разбанен")


@router.message(Command("add_promo"))
async def add_promo(message: Message):
    async with Loading(message):
        user = database.users.get(id=message.from_user.id)

        if not user.is_admin:
            return

        chars = string.digits + string.ascii_letters
        promo = "".join(random.choices(chars, k=6))
        try:
            promo_code = database.promos.get(name=promo)
        except NoResult:
            promo_code = None

        if promo_code:
            promo = "".join(random.choices(chars, k=6))
        mess = f"<b>Новый промокод</b>\n\n<b>Код:</b> <code>{promo}</code>\n"

        items = {}
        usage_count = 1
        description = None

        line_num = 0
        for line in message.text.split("\n"):
            if line_num == 0:
                try:
                    usage_count = int(line.split(" ")[-1])
                except ValueError:
                    usage_count = 1
                mess += f"<b>Кол-во использований:</b> <code>{usage_count}</code>\n"
            elif line_num == 1:
                description = None if line in ["None", "none"] else line
                if description:
                    mess += f"<b>Описание:</b> <i>{description}</i>\n\n"
            elif line_num == 2:
                for item in line.split(", "):
                    name = item.split(" ")[0]
                    quantity = int(item.split(" ")[1])
                    name = name.lower()
                    if get_item(name):
                        items[name] = quantity
                        mess += f"{quantity} {get_item(name).name} {get_item(name).emoji}\n"

            line_num += 1

        code = PromoModel(name=promo, usage_count=usage_count, description=description, items=items)

        database.promos.add(**code.to_dict())

        await message.reply(mess)


@router.message(Command("broadcast"))
async def broadcast_cmd(message: Message):
    user = database.users.get(id=message.from_user.id)

    if not user.is_admin:
        return

    if redis_cache.get("broadcast"):
        await antiflood(message.reply("На данный момент уже идет бродкаст"))
        return

    mess = message.html_text.removeprefix("/broadcast")

    async with MessageEditor(message, title="Бродкаст") as msg:
        redis_cache.set("broadcast", 1)
        msg.exit_funcs.add(partial(redis_cache.delete, "broadcast"))

        start_time = time.monotonic()
        users = database.users.get_all()

        total_count = len(users)
        success_count = 0
        fatal_count = 0

        await msg.write(f"Кол-во пользователей: {total_count}")

        for user in users:
            try:
                await antiflood(message.bot.send_message(user.id, mess))
                success_count += 1
            except TelegramAPIError as e:
                fatal_count += 1
                logger.error(str(e))

        total_time = time.monotonic() - start_time
        await msg.write("Бродкаст закончился")
        await msg.write(f"Время: {total_time:_.2f} с.")
        await msg.write(f"Кол-во юзеров получивших сообщение: {success_count}")
        await msg.write(f"Кол-во ошибок: {fatal_count}")
