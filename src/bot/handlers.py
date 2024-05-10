import random
import string
from datetime import datetime, timedelta
from typing import List

from telebot.types import (
    Message,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
    WebAppInfo
)
from telebot.util import (
    extract_arguments,
    user_link,
    quick_markup,
    content_type_media,
    antiflood,
    chunks,
)
from telebot.apihelper import ApiTelegramException

from helpers.exceptions import NoResult
from base.items import items_list
from helpers.markups import InlineMarkup
from helpers.utils import (
    get_time_difference_string,
    get_item_emoji,
    get_item,
    Loading,
)
from base.player import (
    check_user_stats,
    coin_top,
    get_available_crafts,
    generate_quest,
    generate_exchanger,
    get_available_items_for_use,
    get_or_add_user_item,
)
from base.weather import get_weather

from database.funcs import database
from database.models import ItemModel, PromoModel

from config import bot, event_end_time, event_open, channel_id, chat_id, logger


START_MARKUP = ReplyKeyboardMarkup(resize_keyboard=True)
if event_open:
    START_MARKUP.add(KeyboardButton("Ивент"))

START_MARKUP.add(
    *[
        KeyboardButton("Профиль"),
        KeyboardButton("Дом"),
        KeyboardButton("Инвентарь"),
        KeyboardButton("Квест"),
        KeyboardButton("Магазин"),
        KeyboardButton("Верстак"),
        KeyboardButton("Рейтинг"),
        KeyboardButton("Юз"),
        KeyboardButton("Статы"),
        KeyboardButton("Погода"),
        KeyboardButton("Обменник"),
        KeyboardButton("Гайд"),
    ]
)


@bot.message_handler(commands=["start"])
def start(message: Message):
    with Loading(message):
        user_id = message.from_user.id

        user = database.users.get(id=message.from_user.id)

        mess = (
            f"Здарова {message.from_user.first_name}, добро пожаловать в игру\n\n"
            "Помошь: /help"
        )

        if len(message.text.split("/start ")) != 1:  # pyright: ignore
            param = message.text.split("/start ")[1]  # pyright: ignore
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
                user = database.users.get(id=message.from_user.id)

                coin = random.randint(5000, 15000)
                ref_user.coin += coin
                database.users.update(**ref_user.to_dict())
                bot.send_message(
                    ref_user.id,
                    (
                        f"{user.name} присоеденился к игре блогодаря твой реферальной ссылке\n"
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
            user = user = database.users.get(id=message.reply_to_message.from_user.id)
        else:
            user = database.users.get(id=message.from_user.id)

        check_user_stats(user, message.chat.id)

        mess = (
            f"<b>Профиль {user.name}</b>\n\n"
            f"❤️ Здоровье: {user.health}\n"
            f"🎭 Настроение: {user.mood}\n"
            f"💤 Усталость: {user.fatigue}\n"
            f"🍞 Голод: {user.hunger}\n"
            f"🪙 Бабло: {user.coin}\n"
            f"🏵 Уровень: {user.level}\n"
            f"🎗 Опыт {int(user.xp)}/{int(user.max_xp)}\n"
        )
        bot.reply_to(message, mess)


@bot.message_handler(commands=["bag"])
def bag_cmd(message: Message):
    with Loading(message):
        user = database.users.get(id=message.from_user.id)

        mess = "<b>Рюкзак</b>\n\n"
        inventory = database.items.get_all(**{"owner": user._id})
        if not inventory:
            mess += "<i>Пусто...</i>"
        else:
            sorted_items = sorted(
                inventory, key=lambda item: item.quantity, reverse=True
            )

            for item in sorted_items:
                if item.quantity <= 0:
                    continue
                mess += f"{get_item_emoji(item.name)} {item.name} - {item.quantity}\n"

        bot.reply_to(message, mess)


@bot.message_handler(commands=["items"])
def items_cmd(message: Message):
    with Loading(message):
        mess = f"<b>Предметы</b>\n\n1 / {len(list(chunks(items_list, 6)))}"
        user = database.users.get(id=message.from_user.id)
        markup = markup = InlineMarkup.items_pager(user=user)

        bot.reply_to(message, mess, reply_markup=markup)


@bot.message_handler(commands=["shop"])
def shop_cmd(message: Message):
    with Loading(message):
        args = str(message.text).split(" ")

        if len(args) != 3:
            mess = "<b>🛍Магазин🛍</b>\n\n"
            for item in items_list:
                if not item.price:
                    continue

                mess += f"{item.emoji} {item.name} - {item.price}/шт.\n"
            bot.reply_to(message, mess)
            return

        err_mess = "Что-то не так написал\n" "Надо: <code>/shop буханка 10</code>"

        if len(args) != 3:
            bot.reply_to(message, err_mess)
            return

        user = database.users.get(id=message.from_user.id)

        item_name = args[1]
        try:
            count = int(args[2])
        except (ValueError, IndexError):
            count = 1

        if not get_item(item_name):
            bot.reply_to(message, "Такого придмета не существует")
            return

        item = get_item(item_name)

        if not item.price:
            bot.reply_to(message, "Этот придмет нельзя купить, у него нет цены")
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
                "Чтобы сыграть напиши <code>/casino кол-во</code>"
            )
            bot.reply_to(message, mess)
            return

        try:
            count = int(count)
        except ValueError:
            count = 1

        user = database.users.get(id=message.from_user.id)

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
        user = database.users.get(id=message.from_user.id)

        mess = (
            "<b>🧰Верстак🧰</b>\n\n"
            "Чтобы скрафтить чтото то напиши <code>/craft буханка 1</code>\n\n"
        )

        args = str(message.text).split(" ")

        if not args or len(args) < 2:
            available_crafts = get_available_crafts(user)
            if available_crafts:
                mess += "<b>Доступные крафты</b>\n"
                for craft_data in available_crafts:
                    item_name = craft_data["item_name"]
                    resources = craft_data["resources"]

                    possible_crafts = min(
                        user_count // count for _, count, user_count in resources
                    )
                    craft_str = (
                        f"{get_item_emoji(item_name)} {item_name} - {possible_crafts}\n"
                    )
                    mess += f"{craft_str}"

            bot.reply_to(message, mess)
            return

        name = args[1].lower()
        try:
            count = int(args[2])
        except (ValueError, IndexError):
            count = 1

        if not get_item(name):
            bot.reply_to(message, "Такого придмета не существует")
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
                bot.reply_to(message, "Недостатично придметов")
                return

            user_item.quantity -= craft_item[1] * count
            database.items.update(**user_item.to_dict())

        item = get_or_add_user_item(user, name)

        item.quantity += count
        xp = random.uniform(5.0, 10.0) * count
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

        user = database.users.get(id=message.from_user.id)
        reply_user = database.users.get(id=message.reply_to_message.from_user.id)

        args = message.text.split(" ")

        err_mess = (
            "Что-то не так написал, надо так:\n" "<code>/transfer буханка 10</code>"
        )

        if len(args) < 2:
            bot.reply_to(message, err_mess)
            return

        item = args[1].lower()
        try:
            count = int(args[2])
        except (ValueError, IndexError):
            count = 1

        if item != "бабло":
            item_data = get_or_add_user_item(user, item)
            reply_user_item_data = get_or_add_user_item(reply_user, item)
            logger.debug(item_data.quantity)
            logger.debug(count)

        if item == "бабло":
            if user.coin <= 0:
                bot.reply_to(message, f"У тебя нет <i>{item}</i>")
                return
            elif user.coin <= count:
                bot.reply_to(message, "У тебя недостатично бабла, иди работать")
                return
            user.coin -= count
            reply_user.coin += count
        else:
            if not get_item(item):
                bot.reply_to(
                    message, f"{item}??\nСерёзно?\n\nТакого придмета не существует"
                )
                return
            if (item_data.quantity < count) or (item_data.quantity <= 0):
                bot.reply_to(message, f"У тебя нет <i>{item}</i>")
                logger.debug(item_data.quantity)
                logger.debug(count)
                return

            item_data.quantity -= count
            reply_user_item_data.quantity += count
            database.items.update(**reply_user_item_data.to_dict())
            database.items.update(**item_data.to_dict())

        mess = (
            f"{user.name} подарил {reply_user.name}\n"
            "----------------\n"
            f"{get_item_emoji(item)} {item} {count}"
        )

        database.users.update(**user.to_dict())
        database.users.update(**reply_user.to_dict())

        bot.send_message(message.chat.id, mess)


@bot.message_handler(commands=["event"])
def event_cmd(message: Message):
    with Loading(message):
        user = database.users.get(id=message.from_user.id)

        if event_open is False:
            bot.reply_to(message, "Ивент закончился")
            return

        if event_end_time < datetime.utcnow():
            mess = "Ивент закончился, жди сообщение в новостном канале 💙"
            bot.reply_to(message, mess)
            return

        time_difference = event_end_time - datetime.utcnow()
        time_left = get_time_difference_string(time_difference)

        mess = (
            "<b>Ивент 🦋</b>\n\n"
            "Соберай 🦋 и побеждай\n\n"
            "Бабочек можно получать во время прогулки, в боксе и в сундуке\n\n"
            f"<b>До окончания осталось:</b> {time_left}\n\n"
            "<b>Топ 10 по 🦋</b>\n\n"
        )

        butterflys = [
            get_or_add_user_item(user, "бабочка") for user in database.users.get_all()
        ]
        sorted_butterflys: List[ItemModel] = sorted(
            butterflys, key=lambda butterfly: butterfly.quantity, reverse=True
        )
        for index, butterfly in enumerate(sorted_butterflys, start=1):
            if butterfly.quantity > 0:
                owner = database.users.get(**{"_id": butterfly.owner})
                mess += f"{index}. {owner.name or '<i>неопознаный персонаж</i>'} - {butterfly.quantity}\n"
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
                "🪙": {"callback_data": f"top coin {message.from_user.id}"},
                "🏵": {"callback_data": f"top level {message.from_user.id}"},
                "🐶": {"callback_data": f"top dog_level {message.from_user.id}"},
            }
        )

        bot.reply_to(message, mess, reply_markup=markup)


@bot.message_handler(commands=["use"])
def use_cmd(message: Message):
    with Loading(message):
        user = database.users.get(id=message.from_user.id)

        args = str(message.text).split(" ")

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
                mess = "<b>Доступные придметы для юза</b>\n\n"
            else:
                mess = "Нет доступных придметов для юза"
            bot.reply_to(message, mess, reply_markup=markup)
            return


@bot.message_handler(commands=["ref"])
def ref(message: Message):
    with Loading(message):
        user = database.users.get(id=message.from_user.id)

        mess = (
            "Хочешь заработать?\n"
            "Ты по адресу, пригласи друзей и получи от 5к до 15к бабла\n"
            f"Вот твоя ссылочка: https://t.me/{bot.get_me().username}?start={user.id}"
        )
        bot.reply_to(message, mess)


@bot.message_handler(commands=["add_promo"])
def add_promo(message: Message):
    with Loading(message):
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
        mess = "<b>Новый промокод</b>\n\n" f"<b>Код:</b> <code>{promo}</code>\n"

        items = {}
        usage_count = 1
        description = None

        line_num = 0
        for line in str(message.text).split("\n"):
            if line_num == 0:
                try:
                    usage_count = int(line.split(" ")[-1])
                except ValueError:
                    usage_count = 1
                mess += f"<b>Кол-во использованый:</b> <code>{usage_count}</code>\n"
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
        user = database.users.get(id=message.from_user.id)

        tg_user = bot.get_chat_member(channel_id, message.from_user.id)
        chat_info = bot.get_chat(channel_id)
        bot.delete_message(message.chat.id, message.id)
        if tg_user.status not in ["member", "administrator", "creator"]:
            markup = quick_markup({"Подписатся": {"url": f"t.me/{chat_info.username}"}})
            bot.send_message(
                message.chat.id,
                "Чтобы активировать промо нужно подписатся на новостной канал",
                reply_markup=markup,
            )
            return

        text = str(message.text).split(" ")

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
        user = database.users.get(id=message.from_user.id)

        mess = (
            "<b>Статистика</b>\n\n\n"
            f"<b>[ Казино ]</b>\n"
            f"- Выиграл: {user.casino_win}\n"
            f"- Просрал: {user.casino_loose}\n"
            f"- Профит: {user.casino_win - user.casino_loose}\n\n"
            f"<b>[ Общее ]</b>\n"
            f"- Кол-во дней в игре: {(datetime.utcnow() - user.registered_at).days} д.\n"
            f"- Забанен: {'да' if user.is_banned else 'нет'}\n"
            f"- Админ: {'да' if user.is_admin else 'нет'}"
        )

        bot.reply_to(message, mess)


@bot.message_handler(commands=["quest"])
def quest_cmd(message: Message):
    with Loading(message):
        user = database.users.get(id=message.from_user.id)
        try:
            quest = database.quests.get(**{"owner": user._id})
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
            f"<b>Прогноз погоды</b>\n\n"
            f"{weather.main.temp} °C\n"
            f"{weather.weather.ru_name}"
        )

        try:
            bot.send_photo(
                message.chat.id,
                f"http://openweathermap.org/img/wn/{weather.weather.icon}@2x.png",
                caption=mess,
            )
        except Exception:
            bot.reply_to(message, mess)


@bot.message_handler(commands=["exchanger"])
def exchanger_cmd(message: Message):
    # if True:
    #     bot.reply_to(message, "Временно не работает изза багов :(")
    #     return
    with Loading(message):
        user = database.users.get(id=message.from_user.id)

        if user.level < 5:
            bot.reply_to(message, "Обменник доступен с 5 уровня")
            return

        try:
            exchanger = database.exchangers.get(**{"owner": user._id})
        except NoResult:
            exchanger = generate_exchanger(user)
            database.exchangers.update(**exchanger.to_dict())

        if exchanger.expires <= datetime.utcnow():
            exchanger = generate_exchanger(user)
            database.exchangers.update(**exchanger.to_dict())
        

        mess = (
            "<b>Обменник 🔄</b>\n\n"
            f"<b>Предмет:</b> {exchanger.item} {get_item_emoji(exchanger.item)}\n"
            f"<b>Цена за 1 шт:</b> {exchanger.price} {get_item_emoji('бабло')}\n\n"
            f"Чтобы обеменять напиши <code>/exchanger кол-во</code>"
        )

        args = str(message.text).split(" ")

        if len(args) < 2:
            bot.reply_to(message, mess)
            return

        try:
            quantity = int(args[1])
        except (ValueError, IndexError):
            quantity = 1

        user_item = get_or_add_user_item(user, exchanger.item)

        if not user_item:
            bot.reply_to(message, f"У тебя нет {get_item_emoji(exchanger.item)}")
            return

        if user_item.quantity < quantity:
            bot.reply_to(message, "Тебе не хватает")
            return

        coin = quantity * exchanger.price
        user.coin += coin
        user_item.quantity -= quantity

        database.users.update(**user.to_dict())
        database.items.update(**user_item.to_dict())

        bot.reply_to(
            message,
            f"Обменял {quantity} {get_item_emoji(exchanger.item)} за {coin} {get_item_emoji('бабло')}",
        )


@bot.message_handler(commands=["dog"])
def dog_cmd(message: Message):
    with Loading(message):
        user = database.users.get(id=message.from_user.id)

        try:
            dog = database.dogs.get(**{"owner": user._id})
            print(dog.to_dict())
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

        # current_time = datetime.utcnow()
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
        user = database.users.get(id=message.from_user.id)

        try:
            dog = database.dogs.get(**{"owner": user._id})
        except NoResult:
            dog = None

        if not dog:
            bot.reply_to(message, "У тебя нет собачки")
            return

        try:
            name = message.text.split(" ")[1]  # pyright: ignore
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
            name = str(message.text).split(" ")[1].lower()
        except KeyError:
            bot.reply_to(message, "По моему ты чтото забыл...")
            return

        item = get_item(name)
        if not item:
            mess = "Такого придмета не существует"
        elif item.price:
            mess = f"Прайс {item.name} {item.emoji} ⸻ {item.price} {get_item_emoji('бабло')}"
        else:
            mess = f"У {item.emoji} нет прайса"

        bot.reply_to(message, mess)


@bot.message_handler(commands=["home"])
def home_cmd(message: Message):
    with Loading(message):
        user = database.users.get(id=message.from_user.id)
        mess = "🏠 Дом милый дом"

        markup = InlineMarkup.home_main(user)

        bot.reply_to(message, mess, reply_markup=markup)


@bot.message_handler(commands=["guide"])
def guide_cmd(message: Message):
    # with Loading(message):
    #     mess = "Гайд по LiveBot 🍃"

    #     markup = quick_markup(
    #         {
    #             "Для новичков ✨": {
    #                 "callback_data": f"guide beginner {message.from_user.id}"
    #             },
    #             "Для продвинутых 🔫": {
    #                 "callback_data": f"guide advanced {message.from_user.id}"
    #             },
    #             "Остальное 🧩": {
    #                 "callback_data": f"guide other {message.from_user.id}"
    #             },
    #         },
    #         row_width=1,
    #     )

    #     bot.send_message(message.chat.id, mess, reply_markup=markup)


    mess = "Гайд по LiveBot 🍃"
    markup = InlineKeyboardMarkup()
    if message.chat.type == "private":
        markup.add(
            InlineKeyboardButton("Читать", web_app=WebAppInfo("https://hamletsargsyan.github.io/livebot/guide/"))
        )
    else:
        mess += "\n\nhttps://hamletsargsyan.github.io/livebot/"


    bot.send_message(message.chat.id, mess, reply_markup=markup)

@bot.message_handler(commands=["market"])
def market_cmd(message: Message):
    user = database.users.get(id=message.from_user.id)

    if user.level < 10:
        bot.reply_to(message, "Нужно иметь 10+ лвл")
        return

    database.markets.get_all()
    database.markets.get(owner=user._id)


# ---------------------------------------------------------------------------- #


@bot.message_handler(content_types=["new_chat_members"])
def new_chat_member(message: Message):
    if not message.new_chat_members:
        return

    for new_member in message.new_chat_members:
        if message.chat.id == chat_id:
            mess = f"Привет {user_link(new_member)}, добро пожаловать в оффицеальный чат по лайвботу 💙\n\n"
            bot.send_message(message.chat.id, mess)


@bot.channel_post_handler(content_types=content_type_media)
def handle_channel_post(message: Message):
    if str(message.chat.id) != channel_id:
        return

    for user in database.users.get_all():
        try:
            antiflood(bot.forward_message, user.id, message.chat.id, message.id)
            antiflood(
                bot.send_message,
                user.id,
                "Клавиатура обновлена",
                reply_markup=START_MARKUP,
            )
        except ApiTelegramException:
            continue


@bot.message_handler(content_types=["text"])
def text_message_handler(message: Message):
    user = database.users.get(id=message.from_user.id)

    text = str(message.text).lower()

    if text == "профиль":
        profile_cmd(message)
    elif text in ["инвентарь", "портфель", "инв"]:
        bag_cmd(message)
    elif text.startswith(("магазин", "шоп")):
        shop_cmd(message)
    elif text.startswith(("крафт", "верстак")):
        workbench_cmd(message)
    elif text in ["топ", "рейтинг"]:
        top_cmd(message)
    elif text == "ивент":
        event_cmd(message)
    elif text.startswith("юз"):
        use_cmd(message)
    elif text == "придметы":
        items_cmd(message)
    elif text == "бабло":
        with Loading(message):
            bot.reply_to(message, f"{get_item_emoji('бабло')} Бабло: {user.coin}")
    elif text == "статы":
        stats_cmd(message)
    elif text == "квест":
        quest_cmd(message)
    elif text == "погода":
        weather_cmd(message)
    elif text == "обменник":
        exchanger_cmd(message)
    elif text.startswith("передать"):
        transfer_cmd(message)
    elif text == "собака":
        dog_cmd(message)
    elif text.startswith("прайс"):
        price_cmd(message)
    elif text == "гайд":
        guide_cmd(message)
    elif text == "дом":
        home_cmd(message)
