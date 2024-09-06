import random
import string
from typing import List

from telebot.types import (
    Message,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
    WebAppInfo,
)
from telebot.util import (
    extract_arguments,
    user_link,
    quick_markup,
    chunks,
)

from helpers.enums import ItemType
from helpers.exceptions import ItemNotFoundError, NoResult
from base.items import items_list
from helpers.markups import InlineMarkup
from helpers.utils import (
    check_user_subscription,
    check_version,
    from_user,
    get_middle_item_price,
    get_time_difference_string,
    get_item_emoji,
    get_item,
    Loading,
    get_user_tag,
    increment_achievement_progress,
    only_admin,
    send_channel_subscribe_message,
    utcnow,
)
from base.player import (
    check_user_stats,
    coin_top,
    generate_daily_gift,
    get_available_crafts,
    generate_quest,
    generate_exchanger,
    get_available_items_for_use,
    get_or_add_user_item,
    transfer_countable_item,
)
from base.weather import get_weather

import base.user_input  # noqa

from database.funcs import database
from database.models import ItemModel, PromoModel, UserModel, Violation

from config import bot, config, version


START_MARKUP = ReplyKeyboardMarkup(resize_keyboard=True)
if config.event.open:
    START_MARKUP.add(KeyboardButton("Ивент"))

START_MARKUP.add(
    *[
        KeyboardButton("Профиль"),
        KeyboardButton("Дом"),
        KeyboardButton("Инвентарь"),
        KeyboardButton("Квест"),
        KeyboardButton("Магазин"),
        KeyboardButton("Рынок"),
        KeyboardButton("Верстак"),
        KeyboardButton("Топ"),
        KeyboardButton("Юз"),
        KeyboardButton("Статы"),
        KeyboardButton("Погода"),
        KeyboardButton("Обменник"),
        KeyboardButton("Гайд"),
        KeyboardButton("Достижения"),
    ]
)


@bot.message_handler(commands=["start"])
def start(message: Message):
    with Loading(message):
        user_id = from_user(message).id

        user = database.users.get(id=from_user(message).id)

        mess = (
            f"Здорова {from_user(message).first_name}, добро пожаловать в игру\n\n"
            "Помощь: /help"
        )

        if len(message.text.split("/start ")) != 1:
            param = message.text.split("/start ")[1]
            users_id = [str(user.id) for user in database.users.get_all()]

            if param in users_id:
                if str(user_id) == param:
                    bot.reply_to(message, mess)
                    return
                if user is not None:
                    bot.reply_to(message, mess)
                    return
                ref_user = user = database.users.get(id=param)
                if not ref_user:
                    bot.reply_to(message, mess, reply_markup=START_MARKUP)
                    return
                user = database.users.get(id=from_user(message).id)

                coin = random.randint(5000, 15000)
                ref_user.coin += coin
                database.users.update(**ref_user.to_dict())
                increment_achievement_progress(ref_user, "друзья навеки")

                bot.send_message(
                    ref_user.id,
                    (
                        f"{user.name} присоединился к игре благодаря твой реферальной ссылке\n"
                        f"Ты получил {coin} бабла {get_item_emoji('бабло')}"
                    ),
                )
                return

        if message.chat.type != "private":
            markup = ReplyKeyboardMarkup()
        else:
            markup = START_MARKUP

        bot.reply_to(message, mess, reply_markup=markup)


@bot.message_handler(commands=["help"])
def help(message: Message):
    mess = (
        "<b>Помощь</b>\n\n"
        "<b>Канал:</b> @LiveBotOfficial\n"
        "<b>Чат</b>: @LiveBotOfficialChat\n"
        "<b>Гайд</b>: https://hamletsargsyan.github.io/livebot/guide\n"
    )

    bot.reply_to(message, mess)


@bot.message_handler(commands=["profile"])
def profile_cmd(message: Message):
    with Loading(message):
        if message.reply_to_message:
            user = user = database.users.get(id=from_user(message.reply_to_message).id)
        else:
            user = database.users.get(id=from_user(message).id)

        check_user_stats(user, message.chat.id)

        mess = (
            f"<b>Профиль {user.name}</b>\n\n"
            f"❤️ Здоровье: {user.health}\n"
            f"🎭 Настроение: {user.mood}\n"
            f"💤 Усталость: {user.fatigue}\n"
            f"🍞 Голод: {user.hunger}\n"
            f"🪙 Бабло: {user.coin}\n"
            f"🍀 Удача: {user.luck}\n"
            f"🏵 Уровень: {user.level}\n"
            f"🎗 Опыт {int(user.xp)}/{int(user.max_xp)}\n"
        )
        bot.reply_to(message, mess)


@bot.message_handler(commands=["bag"])
def bag_cmd(message: Message):
    with Loading(message):
        user = database.users.get(id=from_user(message).id)

        mess = "<b>Рюкзак</b>\n\n"
        inventory = database.items.get_all(**{"owner": user._id})
        if not inventory:
            mess += "<i>Пусто...</i>"
        else:
            inventory.sort(
                key=lambda item: item.usage if item.usage else item.quantity,
                reverse=True,
            )
            inventory.sort(key=lambda item: item.quantity, reverse=True)

            for item in inventory:
                if item.quantity <= 0 or (item.usage and item.usage <= 0):
                    continue
                usage = f" ({int(item.usage)}%)" if item.usage else ""
                mess += f"{get_item_emoji(item.name)} {item.name} - {item.quantity}{usage}\n"

        bot.reply_to(message, mess)


@bot.message_handler(commands=["items"])
def items_cmd(message: Message):
    with Loading(message):
        mess = f"<b>Предметы</b>\n\n1 / {len(list(chunks(items_list, 6)))}"
        user = database.users.get(id=from_user(message).id)
        markup = markup = InlineMarkup.items_pager(user=user)

        bot.reply_to(message, mess, reply_markup=markup)


@bot.message_handler(commands=["shop"])
def shop_cmd(message: Message):
    with Loading(message):
        args = message.text.split(" ")

        if len(args) != 3:
            items = list(filter(lambda item: item.price, items_list))
            items.sort(key=lambda item: item.price, reverse=True)  # type: ignore
            mess = "<b>🛍Магазин🛍</b>\n\n"
            for item in items:
                if not item.price:
                    continue

                mess += f"{item.emoji} {item.name} - {item.price}/шт.\n"
            bot.reply_to(message, mess)
            return

        err_mess = (
            "Что-то не так написал\n" "Надо: <code>/shop [имя предмета] [кол-во]</code>"
        )

        if len(args) != 3:
            bot.reply_to(message, err_mess)
            return

        user = database.users.get(id=from_user(message).id)

        item_name = args[1]
        try:
            count = int(args[2])
        except (ValueError, IndexError):
            count = 1

        if not get_item(item_name):
            bot.reply_to(message, "Такого предмета не существует")
            return

        item = get_item(item_name)

        if not item.price:
            bot.reply_to(message, "Этот предмет нельзя купить, у него нет цены")
            return

        price = item.price * count
        if user.coin < price:
            bot.reply_to(message, "У тебя нет столько бабла, иди работать")
            return

        user.coin -= price
        user_item = get_or_add_user_item(user, get_item(item.name).name)

        user_item.quantity += count
        database.users.update(**user.to_dict())
        database.items.update(**user_item.to_dict())

        bot.reply_to(
            message,
            f"Купил {count} {item.name} {get_item_emoji(item.name)} за {price} {get_item_emoji('бабло')}",
        )


@bot.message_handler(commands=["casino"])
def casino(message: Message):
    with Loading(message):
        count = extract_arguments(str(message.text))

        if count == "":
            mess = (
                "<b>🎰Казино🎰</b>\n\n"
                "Решил заработать легкие деньги? Ну давай\n"
                "Шансы 50 на 50\n"
                "Чтобы сыграть напиши <code>/casino [кол-во]</code>"
            )
            bot.reply_to(message, mess)
            return

        try:
            count = int(count)
        except ValueError:
            count = 1

        user = database.users.get(id=from_user(message).id)

        ticket = get_or_add_user_item(user, "билет")

        if (not ticket) or (ticket.quantity <= 0):
            bot.reply_to(
                message,
                f"Чтобы сыграть в казино у тебя должен быть билет {get_item_emoji('билет')}",
            )
            return

        chance = random.randint(0, 10)

        if count > user.coin:
            bot.reply_to(
                message,
                f"Нифига се цифры, у тебя есть только {user.coin} {get_item_emoji('бабло')}",
            )
            return

        if count <= 0:
            count = 1

        if user.coin <= 0:
            bot.reply_to(message, "Кудаа, у тебя нет бабла, иди работать")
            return

        bot.send_dice(message.chat.id, "🎲")
        ticket.quantity -= 1
        if chance <= 5:
            bot.send_message(message.chat.id, f"Блин, сорян\n——————\n-{count}")
            user.coin -= count
            user.casino_loose += count

        else:
            bot.send_message(message.chat.id, f"Нифига се\n——————\n+{count * 2}")
            user.coin += count * 2
            user.casino_win += count * 2

        database.users.update(**user.to_dict())
        database.items.update(**ticket.to_dict())
        check_user_stats(user, message.chat.id)


@bot.message_handler(commands=["workbench", "craft"])
def workbench_cmd(message: Message):
    with Loading(message):
        user = database.users.get(id=from_user(message).id)

        mess = (
            "<b>🧰Верстак🧰</b>\n\n"
            "Чтобы скрафтить что-то то напиши <code>/craft [имя предмета] [кол-во]</code>\n\n"
        )

        args = message.text.split(" ")

        if not args or len(args) < 2:
            available_crafts = get_available_crafts(user)
            if available_crafts:
                print(available_crafts)
                mess += "<b>Доступные крафты</b>\n"
                for craft_data in available_crafts:
                    item_name = craft_data["item_name"]
                    resources = craft_data["resources"]

                    possible_crafts = min(
                        user_item["user_item_quantity"] // user_item["item_count"]
                        for user_item in resources
                    )

                    print(
                        get_item_emoji(item_name), item_name, get_item(item_name).emoji
                    )
                    craft_str = (
                        f"{get_item_emoji(item_name)} {item_name} - {possible_crafts}\n"
                    )
                    mess += f"{craft_str}"
            print(mess)
            bot.reply_to(message, mess)
            return

        name = args[1].lower()
        try:
            count = int(args[2])
        except (ValueError, IndexError):
            count = 1

        if not get_item(name):
            bot.reply_to(message, "Такого предмета не существует")
            return

        item_data = get_item(name)

        if not item_data.craft:
            bot.reply_to(message, f"У {item_data.emoji} нет крафта")
            return

        craft = item_data.craft

        for craft_item in craft.items():
            user_item = get_or_add_user_item(user, craft_item[0])
            if (
                (not user_item)
                or (user_item.quantity <= 0)
                or (user_item.quantity < craft_item[1] * count)
            ):
                bot.reply_to(message, "Недостаточно предметов")
                return

            user_item.quantity -= craft_item[1] * count
            database.items.update(**user_item.to_dict())

        item = get_or_add_user_item(user, name)

        item.quantity += count
        xp = random.uniform(5.0, 10.0) * count
        if random.randint(1, 100) < user.luck:
            xp += random.uniform(2.3, 6.7)

        user.xp += xp

        database.items.update(**item.to_dict())
        database.users.update(**user.to_dict())
        bot.reply_to(
            message, f"Скрафтил {count} {name} {get_item_emoji(name)}\n+ {int(xp)} хп"
        )

        check_user_stats(user, message.chat.id)


@bot.message_handler(commands=["transfer"])
def transfer_cmd(message: Message):
    with Loading(message):
        if not message.reply_to_message:
            bot.reply_to(message, "Кому кидать собрался??")
            return

        user = database.users.get(id=from_user(message).id)
        reply_user = database.users.get(id=from_user(message.reply_to_message).id)

        args = message.text.split(" ")

        err_mess = (
            "Что-то не так написал, надо так:\n"
            "<code>/transfer [имя предмета] [кол-во]</code>"
        )

        if len(args) < 2:
            bot.reply_to(message, err_mess)
            return

        item_name = args[1].lower()
        try:
            item = get_item(item_name)
        except ItemNotFoundError:
            bot.reply_to(
                message, f"{item_name}??\nСерьёзно?\n\nТакого предмета не существует"
            )
            return

        try:
            quantity = int(args[2])
        except (ValueError, IndexError):
            quantity = 1

        if item_name == "бабло":
            if user.coin <= 0:
                bot.reply_to(message, f"У тебя нет <i>{item_name}</i>")
                return
            elif user.coin <= quantity:
                bot.reply_to(message, "У тебя Недостаточно бабла, иди работать")
                return
            user.coin -= quantity
            reply_user.coin += quantity
        else:
            if item.type == ItemType.USABLE:
                mess = "Выбери какой"
                markup = InlineMarkup.transfer_usable_items(user, reply_user, item_name)

                bot.reply_to(message, mess, reply_markup=markup)
                return
            else:
                user_item = get_or_add_user_item(user, item_name)

                if (user_item.quantity < quantity) or (user_item.quantity <= 0):
                    bot.reply_to(message, f"У тебя нет <i>{item_name}</i>")
                    return
                transfer_countable_item(user_item, quantity, reply_user)

        mess = (
            f"{user.name} подарил {reply_user.name}\n"
            "----------------\n"
            f"{item.emoji} {item_name} {quantity}"
        )

        database.users.update(**user.to_dict())
        database.users.update(**reply_user.to_dict())

        bot.send_message(message.chat.id, mess)


@bot.message_handler(commands=["event"])
def event_cmd(message: Message):
    with Loading(message):
        user = database.users.get(id=from_user(message).id)

        if config.event.open is False:
            if config.event.start_time < utcnow():
                bot.reply_to(message, "Ивент закончился")
            else:
                bot.reply_to(
                    message,
                    f"До начала ивента осталось {get_time_difference_string(config.event.start_time - utcnow())}",
                )
            return

        time_difference = config.event.end_time - utcnow()
        time_left = get_time_difference_string(time_difference)

        mess = (
            "<b>Ивент 🦋</b>\n\n"
            "Собирай 🦋 и побеждай\n\n"
            "Бабочек можно получать во время прогулки, в боксе и в сундуке\n\n"
            f"<b>До окончания осталось:</b> {time_left}\n\n"
            "<b>Топ 10 по 🦋</b>\n\n"
        )

        butterflies = [
            get_or_add_user_item(user, "бабочка") for user in database.users.get_all()
        ]
        sorted_butterflies: List[ItemModel] = sorted(
            butterflies, key=lambda butterfly: butterfly.quantity, reverse=True
        )
        for index, butterfly in enumerate(sorted_butterflies, start=1):
            if butterfly.quantity > 0:
                owner = database.users.get(**{"_id": butterfly.owner})
                mess += f"{index}. {owner.name or '<i>неопознанный персонаж</i>'} - {butterfly.quantity}\n"
            if index == 10:
                break

        butterfly = get_or_add_user_item(user, "бабочка")
        mess += f"\n\nТы собрал: {butterfly.quantity}"
        bot.reply_to(message, mess)


@bot.message_handler(commands=["top"])
def top_cmd(message: Message):
    with Loading(message):
        mess = coin_top()

        markup = quick_markup(
            {
                "🪙": {"callback_data": f"top coin {from_user(message).id}"},
                "🏵": {"callback_data": f"top level {from_user(message).id}"},
                "🐶": {"callback_data": f"top dog_level {from_user(message).id}"},
            }
        )

        bot.reply_to(message, mess, reply_markup=markup)


@bot.message_handler(commands=["use"])
def use_cmd(message: Message):
    with Loading(message):
        user = database.users.get(id=from_user(message).id)

        args = message.text.split(" ")

        if len(args) < 2:
            markup = InlineKeyboardMarkup()
            buttons = []
            items = get_available_items_for_use(user)

            for user_item in items:
                item = get_item(user_item.name)
                buttons.append(
                    InlineKeyboardButton(
                        f"{item.emoji} {user_item.quantity}",
                        callback_data=f"use {item.translit()} {user.id}",
                    )
                )

            markup.add(*buttons)

            if items:
                mess = "<b>Доступные предметы для юза</b>\n\n"
            else:
                mess = "Нет доступных предметов для юза"
            bot.reply_to(message, mess, reply_markup=markup)
            return


@bot.message_handler(commands=["ref"])
def ref(message: Message):
    with Loading(message):
        user = database.users.get(id=from_user(message).id)

        mess = (
            "Хочешь заработать?\n"
            "Ты по адресу, пригласи друзей и получи от 5к до 15к бабла\n"
            f"Вот твоя ссылочка: https://t.me/{bot.get_me().username}?start={user.id}"
        )
        bot.reply_to(message, mess)


@bot.message_handler(commands=["add_promo"])
def add_promo(message: Message):
    with Loading(message):
        user = database.users.get(id=from_user(message).id)

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
        mess = "<b>Новый промокод</b>\n\n" f"<b>Код:</b> <code>{promo}</code>\n"

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
                        mess += (
                            f"{quantity} {get_item(name).name} {get_item(name).emoji}\n"
                        )

            line_num += 1

        code = PromoModel(
            name=promo, usage_count=usage_count, description=description, items=items
        )

        database.promos.add(**code.to_dict())

        bot.reply_to(message, mess)


@bot.message_handler(commands=["promo"])
def promo(message: Message) -> None:
    with Loading(message):
        user = database.users.get(id=from_user(message).id)

        bot.delete_message(message.chat.id, message.id)
        if not check_user_subscription(user):
            send_channel_subscribe_message(message)
            return

        text = message.text.split(" ")

        if len(text) != 1:
            text = text[1]

            code = database.promos.get(name=text)
            if code:
                promo_users = code.users
                if user.id in promo_users:
                    bot.send_message(
                        message.chat.id, "Ты уже активировал этот промокод"
                    )
                    return

                if code.is_used:
                    bot.send_message(message.chat.id, "Этот промокод уже активировали")
                    return

                code.usage_count -= 1

                if code.usage_count <= 0:
                    code.usage_count = 0
                    code.is_used = True

                mess = f"Ухтыы, {user.name} активировал промо и получил\n\n"
                for item in code.items:
                    if item == "бабло":
                        user.coin += code.items[item]
                        database.users.update(**user.to_dict())
                    else:
                        user_item = get_or_add_user_item(user, item)
                        user_item.quantity += code.items[item]
                        database.items.update(**user_item.to_dict())
                    mess += f"+ {code.items[item]} {item} {get_item_emoji(item)}\n"
                promo_users.append(user.id)
                code.users = promo_users

                database.promos.update(**code.to_dict())
                bot.send_sticker(
                    message.chat.id,
                    "CAACAgIAAxkBAAEpjI9l0i13xK0052Ruta0D5a5lWozGBgACHQMAAladvQrFMjBk7XkPEzQE",
                )
                bot.send_message(message.chat.id, mess)
            else:
                bot.send_message(message.chat.id, "Такого промокода не существует")


@bot.message_handler(commands=["stats"])
def stats_cmd(message: Message):
    with Loading(message):
        user = database.users.get(id=from_user(message).id)

        mess = (
            "<b>Статистика</b>\n\n\n"
            f"<b>[ Казино ]</b>\n"
            f"- Выиграл: {user.casino_win}\n"
            f"- Просрал: {user.casino_loose}\n"
            f"- Профит: {user.casino_win - user.casino_loose}\n\n"
            f"<b>[ Общее ]</b>\n"
            f"- Кол-во дней в игре: {(utcnow() - user.registered_at).days} д.\n"
            f"- Забанен: {'да' if user.is_banned else 'нет'}\n"
            f"- Админ: {'да' if user.is_admin else 'нет'}"
        )

        bot.reply_to(message, mess)


@bot.message_handler(commands=["quest"])
def quest_cmd(message: Message):
    with Loading(message):
        user = database.users.get(id=from_user(message).id)
        try:
            quest = database.quests.get(owner=user._id)
        except NoResult:
            quest = None

        if not quest:
            quest = generate_quest(user)
        if not user.new_quest_coin_quantity:
            user.new_quest_coin_quantity = 2

        item = get_or_add_user_item(user, quest.name)

        finish_button_text = (
            f"{item.quantity} / {quest.quantity}"
            if item.quantity < quest.quantity
            else "Завершить"
        )
        markup = InlineKeyboardMarkup()
        markup.add(
            *[
                InlineKeyboardButton(
                    finish_button_text, callback_data=f"finish_quest {user.id}"
                ),
                InlineKeyboardButton("Пропуск", callback_data=f"skip_quest {user.id}"),
            ]
        )

        mess = (
            "<b>Квест</b>\n\n"
            f"<i>Собери {quest.quantity} {quest.name} {get_item_emoji(quest.name)}</i>\n\n"
            f"<b>Награда:</b> {quest.reward} {get_item_emoji('бабло')}"
        )

        bot.reply_to(message, mess, reply_markup=markup)


@bot.message_handler(commands=["weather"])
def weather_cmd(message: Message):
    with Loading(message):
        weather = get_weather()

        mess = (
            f"<b>{weather.weather.emoji} Прогноз погоды</b>\n\n"
            f"{weather.main.temp} °C\n"
            f"{weather.weather.ru_name}"
        )

        bot.reply_to(message, mess)


@bot.message_handler(commands=["exchanger"])
def exchanger_cmd(message: Message):
    # if True:
    #     bot.reply_to(
    #         message,
    #         "Временно не работает из-за <a href='https://github.com/HamletSargsyan/livebot/issues/18'>бага</a> :(",
    #     )
    #     return
    with Loading(message):
        user = database.users.get(id=from_user(message).id)
        markup = quick_markup(
            {
                "Гайд": {
                    "url": "https://hamletsargsyan.github.io/livebot/guide/#обменник"
                }
            }
        )

        if user.level < 5:
            bot.reply_to(message, "Обменник доступен с 5 уровня", reply_markup=markup)
            return

        try:
            exchanger = database.exchangers.get(owner=user._id)
        except NoResult:
            exchanger = generate_exchanger(user)

        if exchanger.expires < utcnow():
            exchanger = generate_exchanger(user)
            database.exchangers.update(**exchanger.to_dict())

        mess = (
            "<b>Обменник 🔄</b>\n\n"
            f"<b>Предмет:</b> {exchanger.item} {get_item_emoji(exchanger.item)}\n"
            f"<b>Цена за 1 шт:</b> {exchanger.price} {get_item_emoji('бабло')}\n"
            f"<b>Новый предмет появится через:</b> {get_time_difference_string(exchanger.expires - utcnow())}\n"
        )

        args = message.text.split(" ")

        if len(args) < 2:
            bot.reply_to(message, mess, reply_markup=markup)
            return

        try:
            quantity = int(args[1])
        except (ValueError, IndexError):
            quantity = 1

        user_item = get_or_add_user_item(user, exchanger.item)

        if not user_item:
            bot.reply_to(
                message,
                f"У тебя нет {get_item_emoji(exchanger.item)}",
                reply_markup=markup,
            )
            return

        if user_item.quantity < quantity:
            bot.reply_to(message, "Тебе не хватает", reply_markup=markup)
            return

        coin = quantity * exchanger.price
        user.coin += coin
        user_item.quantity -= quantity

        database.users.update(**user.to_dict())
        database.items.update(**user_item.to_dict())

        bot.reply_to(
            message,
            f"Обменял {quantity} {get_item_emoji(exchanger.item)} за {coin} {get_item_emoji('бабло')}",
            reply_markup=markup,
        )


@bot.message_handler(commands=["dog"])
def dog_cmd(message: Message):
    with Loading(message):
        user = database.users.get(id=from_user(message).id)

        try:
            dog = database.dogs.get(owner=user._id)
        except NoResult:
            dog = None

        if not dog:
            bot.reply_to(message, "У тебя нет собачки")
            return

        mess = (
            f"<b>{dog.name}</b>\n\n"
            f"Здоровье: {dog.health}\n"
            f"Усталость: {dog.fatigue}\n"
            f"Голод: {dog.hunger}\n"
            f"Уровень: {dog.level}\n"
            f"Опыт {int(dog.xp)}/{int(dog.max_xp)}\n"
        )

        # current_time = utcnow()
        # time_difference = current_time - user.dog.sleep_time

        # sleep_text = "Уложить спать"
        # sleep_callback = f"dog sleep {user.id}"
        # if time_difference <= timedelta(minutes=1):
        #     sleep_text = "Пробудить"
        #     sleep_callback = f"dog wakeup {user.id}"

        markup = quick_markup(
            {
                "Кормить": {"callback_data": f"dog feed {user.id}"},
                # sleep_text: {"callback_data": sleep_callback}
            }
        )

        bot.reply_to(message, mess, reply_markup=markup)


@bot.message_handler(commands=["rename_dog"])
def rename_dog_command(message: Message):
    with Loading(message):
        user = database.users.get(id=from_user(message).id)

        try:
            dog = database.dogs.get(owner=user._id)
        except NoResult:
            dog = None

        if not dog:
            bot.reply_to(message, "У тебя нет собачки")
            return

        try:
            name = message.text.split(" ")[1]
        except KeyError:
            bot.reply_to(message, "По моему ты забыл написать имя")
            return

        dog.name = name
        database.dogs.update(**dog.to_dict())

        bot.reply_to(message, "Переименовал собачку")


@bot.message_handler(commands=["price"])
def price_cmd(message: Message):
    with Loading(message):
        try:
            name = message.text.split(" ")[1].lower()
        except KeyError:
            bot.reply_to(message, "По моему ты что-то забыл...")
            return

        try:
            item = get_item(name)
        except ItemNotFoundError:
            bot.reply_to(message, "такого предмета не существует")
            return
        price = get_middle_item_price(item.name)
        if not item:
            mess = "Такого предмета не существует"
        elif price:
            mess = f"Прайс {item.name} {item.emoji} ⸻ {price} {get_item_emoji('бабло')}"
        else:
            mess = f"У {item.emoji} пока нет прайса"

        bot.reply_to(message, mess)


@bot.message_handler(commands=["home"])
def home_cmd(message: Message):
    with Loading(message):
        user = database.users.get(id=from_user(message).id)
        mess = "🏠 Дом милый дом"

        markup = InlineMarkup.home_main(user)

        bot.reply_to(message, mess, reply_markup=markup)


@bot.message_handler(commands=["guide"])
def guide_cmd(message: Message):
    mess = "Гайд по LiveBot 🍃"
    markup = InlineKeyboardMarkup()
    guide_url = "https://hamletsargsyan.github.io/livebot/guide"
    if message.chat.type == "private":
        markup.add(
            InlineKeyboardButton(
                "Читать",
                web_app=WebAppInfo(guide_url),
            )
        )
    else:
        mess += f"\n\n{guide_url}"

    bot.send_message(message.chat.id, mess, reply_markup=markup)


@bot.message_handler(commands=["market"])
def market_cmd(message: Message):
    user = database.users.get(id=from_user(message).id)

    mess = "<b>Рынок</b>\n\n"

    market_items = database.market_items.get_all()
    markup = InlineMarkup.market_pager(user)
    mess += f"1 / {len(list(chunks(market_items, 6)))}"

    bot.reply_to(message, mess, reply_markup=markup)


@bot.message_handler(commands=["daily_gift"])
def daily_gift_cmd(message: Message):
    user = database.users.get(id=from_user(message).id)

    if not check_user_subscription(user):
        send_channel_subscribe_message(message)
        return

    try:
        daily_gift = database.daily_gifts.get(owner=user._id)
    except NoResult:
        daily_gift = generate_daily_gift(user)

    mess = "<b>Ежедневный подарок</b>"

    if daily_gift.next_claimable_at <= utcnow():
        daily_gift = generate_daily_gift(user)

    markup = InlineMarkup.daily_gift(user, daily_gift)
    bot.reply_to(message, mess, reply_markup=markup)


@bot.message_handler(commands=["version"])
def version_cmd(message: Message):
    mess = f"<b>Версия бота</b>: <code>{version}</code> | <i>{check_version()}</i>\n"
    markup = quick_markup(
        {
            "Релиз": {
                "url": f"https://github.com/HamletSargsyan/livebot/releases/tag/v{version}"
            }
        }
    )
    bot.reply_to(message, mess, reply_markup=markup)


@bot.message_handler(commands=["time"])
def time_cmd(message: Message):
    time = utcnow().strftime("%H:%M:%S %d.%m.%Y")
    mess = f"Сейчас <code>{time}</code> по UTC"
    bot.reply_to(message, mess)


@bot.message_handler(commands=["achievements"])
def achievements_cmd(message: Message):
    user = database.users.get(id=message.from_user.id)

    markup = InlineMarkup.achievements(user)

    mess = "Достижения"
    bot.reply_to(message, mess, reply_markup=markup)


@bot.message_handler(commands=["rules"])
def rules_cmd(message: Message):
    mess = "Правила"

    markup = quick_markup(
        {"Читать": {"url": "https://hamletsargsyan.github.io/livebot/rules"}}
    )

    bot.reply_to(message, mess, reply_markup=markup)


@bot.message_handler(commands=["warn"])
@only_admin
def warn_cmd(message: Message, user: UserModel):
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


# ---------------------------------------------------------------------------- #


@bot.message_handler(content_types=["new_chat_members"])
def new_chat_member(message: Message):
    if not message.new_chat_members:
        return

    for new_member in message.new_chat_members:
        if str(message.chat.id) == config.telegram.chat_id:
            mess = f"Привет {user_link(new_member)}, добро пожаловать в официальный чат по лайвботу 💙\n\n"
            bot.send_message(message.chat.id, mess)


@bot.message_handler(content_types=["text"])
def text_message_handler(message: Message):
    user = database.users.get(id=from_user(message).id)
    text = message.text.lower().strip()

    match text:
        case "профиль":
            profile_cmd(message)
        case "инвентарь" | "портфель" | "инв":
            bag_cmd(message)
        case _ if text.startswith(("магазин", "шоп")):
            shop_cmd(message)
        case _ if text.startswith(("крафт", "верстак")):
            workbench_cmd(message)
        case "топ" | "рейтинг":
            top_cmd(message)
        case "ивент":
            event_cmd(message)
        case _ if text.startswith("юз"):
            use_cmd(message)
        case "предметы":
            items_cmd(message)
        case "бабло":
            bot.reply_to(message, f"{get_item_emoji('бабло')} Бабло: {user.coin}")
        case "статы":
            stats_cmd(message)
        case "квест":
            quest_cmd(message)
        case "погода":
            weather_cmd(message)
        case "обменник":
            exchanger_cmd(message)
        case _ if text.startswith("передать"):
            transfer_cmd(message)
        case "собака":
            dog_cmd(message)
        case _ if text.startswith("прайс"):
            price_cmd(message)
        case "гайд":
            guide_cmd(message)
        case "дом":
            home_cmd(message)
        case "рынок":
            market_cmd(message)
        case "достижения" | "ачивки":
            achievements_cmd(message)
