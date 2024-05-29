import random
from datetime import datetime, timedelta

from bson import ObjectId
from telebot.util import quick_markup, chunks
from telebot.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from telebot.apihelper import ApiTelegramException
import toml

from helpers.enums import ItemRarity
from helpers.exceptions import NoResult
from helpers.markups import InlineMarkup
from base.player import (
    check_user_stats,
    coin_top,
    dog_level_top,
    generate_quest,
    get_or_add_user_item,
    level_top,
    use_item,
    get_available_items_for_use,
    game,
    sleep,
    street,
    work,
)
from base.items import items_list
from helpers.utils import (
    get_item_count_for_rarity,
    get_item_emoji,
    get_middle_item_price,
    get_time_difference_string,
    get_item,
    get_user_tag,
)

from database.models import DogModel
from database.funcs import database

from config import GUIDE_FILE_PATH, bot


@bot.callback_query_handler(lambda c: c.data.startswith("dog"))
def dog_callback(call: CallbackQuery):
    data = call.data.split(" ")
    user = database.users.get(id=call.from_user.id)

    try:
        dog = database.dogs.get(**{"owner": user._id})
    except NoResult:
        dog = None

    if not isinstance(call.message, Message):
        return

    if data[-1] != str(user.id):
        return
    elif data[1] == "leave":
        bot.delete_message(call.message.chat.id, call.message.id)
        bot.send_sticker(
            call.message.chat.id,
            "CAACAgIAAxkBAAEpvztl21ybsmS9RVqaYhV8ZtA353n4HgACJwEAAjDUnRGOYUDc7Hyw5TQE",
        )
        bot.send_message(call.message.chat.id, "Прогнал бедную собачку(")
        return
    elif data[1] == "friend":
        date = datetime.utcfromtimestamp(call.message.date)
        current_time = datetime.utcnow()
        time_difference = current_time - date

        if time_difference >= timedelta(minutes=1):
            bot.delete_message(call.message.chat.id, call.message.id)
            bot.answer_callback_query(
                call.id, "Пока ты думал псина сбежала", show_alert=True
            )
            return

        item = get_or_add_user_item(user, "кость")

        if item.quantity <= int(data[2]):
            bot.answer_callback_query(
                call.id,
                f"Тебе не хватает 🦴, нужно {data[2]} а у тебя {item.quantity}",
                show_alert=True,
            )
            return

        dog = DogModel(user=user)
        dog.name = f"Собачка-{user.id}"
        database.dogs.add(**dog.to_dict())

        bot.delete_message(call.message.chat.id, call.message.id)
        bot.send_sticker(
            call.message.chat.id,
            "CAACAgIAAxkBAAEpvz9l211Kyfi280mwFR6XMKUhzMXbiwACGAEAAjDUnREiQ2-IziTqFTQE",
        )
        bot.send_message(
            call.message.chat.id,
            "Завел собачку 🐶\n\nНапиши /rename_dog [имя] чтобы дать имя пёсику",
        )
        return
    elif data[1] == "feed" and dog:
        if dog.hunger == 0:
            bot.answer_callback_query(
                call.id, f"{dog.name} не голоден", show_alert=True
            )
            return
        item = get_or_add_user_item(user, "мясо")

        quantity = dog.level * 2

        if item.quantity < quantity:
            bot.answer_callback_query(
                call.id,
                f"Тебе не хватает мяса, нужно {quantity} а у тебя {item.quantity}",
                show_alert=True,
            )
            return
        item.quantity -= quantity
        count = random.randint(1, 10)
        dog.hunger -= count
        dog.xp += random.uniform(0.1, 0.3)
        bot.answer_callback_query(
            call.id,
            f"{dog.name} поел мяса и востановил {count} едениц голода",
            show_alert=True,
        )
        database.dogs.update(**dog.to_dict())
        database.items.update(**item.to_dict())

        check_user_stats(user, call.message.chat.id)

        mess = (
            f"<b>{dog.name}</b>\n\n"
            f"Здоровье: {dog.health}\n"
            f"Усталость: {dog.fatigue}\n"
            f"Голод: {dog.hunger}\n"
            f"Уровень: {dog.level}\n"
            f"Опыт {int(dog.xp)}/{int(dog.max_xp)}\n"
        )

        markup = quick_markup(
            {
                "Кормить": {"callback_data": f"dog feed {user.id}"},
                # "Уложить спать": {"callback_data": f"dog sleep {user.id}"}
            }
        )
        bot.edit_message_text(
            mess, call.message.chat.id, call.message.id, reply_markup=markup
        )
    elif data[1] == "sleep" and dog:
        current_time = datetime.utcnow()
        time_difference = current_time - dog.sleep_time
        if time_difference <= timedelta(minutes=1):
            bot.answer_callback_query(
                call.id,
                f"{dog.name} спит, жди {get_time_difference_string(time_difference - timedelta(minutes=1))}",
                show_alert=True,
            )
            return

        dog.sleep_time = datetime.utcnow()
        time_difference = current_time - dog.sleep_time

        bot.answer_callback_query(
            call.id,
            f"{dog.name} пошел спать, проснется через {get_time_difference_string(time_difference - timedelta(hours=1))}",
            show_alert=True,
        )
    elif data[1] == "wakeup" and dog:
        bot.answer_callback_query(call.id, f"{dog.name} проснулся", show_alert=True)
        dog.sleep_time = datetime.utcnow()

    database.users.update(**user.to_dict())
    if dog:
        database.dogs.update(**dog.to_dict())
    check_user_stats(user)


@bot.callback_query_handler(lambda c: c.data.startswith("skip_quest"))
def new_quest_callback(call: CallbackQuery):
    if call.data.split(" ")[-1] != str(call.from_user.id):
        return

    if not isinstance(call.message, Message):
        return

    user = database.users.get(id=call.from_user.id)

    if not user.new_quest_coin_quantity:
        user.new_quest_coin_quantity = 2

    if user.new_quest_coin_quantity > user.coin:
        bot.answer_callback_query(
            call.id,
            f"У тебя недостатично бабла. Чтобы получить ноый квест надо иметь {user.new_quest_coin_quantity}",
            show_alert=True,
        )
        return

    generate_quest(user)
    user.coin -= user.new_quest_coin_quantity
    user.new_quest_coin_quantity += random.randint(10, 20)
    database.users.update(**user.to_dict())

    bot.answer_callback_query(
        call.id,
        "Ты получил новый квест, напиши /quest чтобы посмотреть",
        show_alert=True,
    )


@bot.callback_query_handler(lambda c: c.data.startswith("finish_quest"))
def finish_quest_callback(call: CallbackQuery):
    if call.data.split(" ")[-1] != str(call.from_user.id):
        return

    if not isinstance(call.message, Message):
        return

    user = database.users.get(id=call.from_user.id)

    try:
        quest = database.quests.get(**{"owner": user._id})
    except NoResult:
        quest = generate_quest(user)

    item = get_or_add_user_item(user, quest.name)

    if item.quantity < quest.quantity:
        bot.answer_callback_query(call.id, "Кудааа, тебе не хватает", show_alert=True)
        return

    item.quantity -= quest.quantity
    user.xp += quest.xp
    user.coin += quest.reward
    database.users.update(**user.to_dict())
    database.items.update(**item.to_dict())

    mess = (
        "Ураа, ты завершил квест\n"
        f"+ {int(quest.xp)} хп\n"
        f"+ {quest.reward} бабло {get_item_emoji('бабло')}\n\n"
        "Ты выполнил квест за "
    )

    total_time: timedelta = datetime.utcnow() - quest.start_time
    mess += get_time_difference_string(total_time)

    generate_quest(user)
    bot.delete_message(call.message.chat.id, call.message.id)

    user_message = call.message.reply_to_message
    bot.send_sticker(
        call.message.chat.id,
        "CAACAgIAAxkBAAEpslFl2JwAAaZFMa3RM-3fKaHU7RYrOSQAAoIPAAJ73EFKS4aLwGmJ_Ok0BA",
    )
    if user_message:
        bot.reply_to(user_message, mess)
    else:
        bot.send_message(call.message.chat.id, mess)

    check_user_stats(user, call.message.chat.id)


@bot.callback_query_handler(lambda c: c.data.startswith("use"))
def use_callback(call: CallbackQuery):
    if call.data.split(" ")[-1] != str(call.from_user.id):
        return

    user = database.users.get(id=call.from_user.id)

    item = get_item(call.data.split(" ")[1])

    if not call.message.reply_to_message:
        return

    use_item(call.message.reply_to_message, item.name)

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

    items = get_available_items_for_use(user)

    if not items:
        mess = "Нет доступных придметов для юза"
        bot.edit_message_text(mess, call.message.chat.id, call.message.id)

    bot.edit_message_reply_markup(
        call.message.chat.id, call.message.id, reply_markup=markup
    )


@bot.callback_query_handler(lambda c: c.data.startswith("item_info_main"))
def item_info_main_callback(call: CallbackQuery):
    if call.data.split(" ")[-1] != str(call.from_user.id):
        return

    try:
        user = database.users.get(id=call.from_user.id)
        action = call.data.split(" ")[1]
        pos = int(call.data.split(" ")[2])
        max_pos = len(list(chunks(items_list, 6))) - 1

        if action == "next":
            pos += 1
        elif action == "back":
            pos -= 1
        elif action == "start":
            pos = 0
        elif action == "end":
            pos = max_pos

        if pos < 0:
            raise IndexError

        mess = f"<b>Предметы</b>\n\n{pos + 1} / {max_pos + 1}"
        markup = InlineMarkup.items_pager(user=user, index=int(pos))

        bot.edit_message_text(
            mess, call.message.chat.id, call.message.id, reply_markup=markup
        )
    except (IndexError, ApiTelegramException):
        bot.answer_callback_query(call.id, "Дальше ничо нету", show_alert=True)


@bot.callback_query_handler(lambda c: c.data.startswith("item_info"))
def item_info_callback(call: CallbackQuery):
    if call.data.split(" ")[-1] != str(call.from_user.id):
        return

    item = get_item(call.data.split(" ")[1])
    pos = call.data.split(" ")[2]

    markup = quick_markup(
        {"Назад": {"callback_data": f"item_info_main None {pos} {call.from_user.id}"}}
    )

    craft = ""
    if item.craft:
        craft = ", ".join(
            [
                f"{get_item_emoji(name)} {name} {count}"
                for name, count in item.craft.items()
            ]
        )

    mess = (
        f"<b>{item.emoji} {item.name}</b>\n\n"
        f"<b>Редкость:</b> {item.rarity.value}\n\n"
        f"<b>Описание:</b> <i>{item.desc}</i>\n\n"
        + (f"<b>Крафт:</b> <i>{craft}</i>\n" if item.craft else "")
    )

    bot.edit_message_text(
        mess, call.message.chat.id, call.message.id, reply_markup=markup
    )


@bot.callback_query_handler(lambda c: c.data.startswith("trader"))
def trader_callback(call: CallbackQuery):
    data = call.data.split(" ")
    if data[-1] != str(call.from_user.id):
        return

    if not isinstance(call.message, Message):
        return
    user = database.users.get(id=call.from_user.id)

    if data[1] == "leave":
        bot.delete_message(call.message.chat.id, call.message.id)
        bot.send_sticker(
            call.message.chat.id,
            "CAACAgEAAxkBAAEpxYVl3KqB7JnvbmYgXQqVAhUQYbnyXwACngIAAv9iMUeUcUiHcCrhSTQE",
        )
        bot.send_message(call.message.chat.id, "Пф... нехочешь как хочешь")
        return
    elif data[1] == "trade":
        item = get_item(data[2])
        quantity = int(data[3])
        price = int(data[4])
        user_item = get_or_add_user_item(user, item.name)

        if user.coin < price:
            bot.answer_callback_query(
                call.id, f"Тебе нехватает {price - user.coin} бабла", show_alert=True
            )
            return

        user.coin -= price
        user_item.quantity += quantity
        bot.delete_message(call.message.chat.id, call.message.id)
        bot.send_message(
            call.message.chat.id,
            f"{user.name} купил у торговца {quantity} {item.name} {item.emoji} за {price}",
        )
        return


@bot.callback_query_handler(lambda c: c.data.startswith("top"))
def top_callback(call: CallbackQuery):
    data = call.data.split(" ")
    print(data)
    if data[-1] != str(call.from_user.id):
        return

    markup = quick_markup(
        {
            "🪙": {"callback_data": f"top coin {call.from_user.id}"},
            "🏵": {"callback_data": f"top level {call.from_user.id}"},
            "🐶": {"callback_data": f"top dog_level {call.from_user.id}"},
        }
    )

    tops = {"coin": coin_top(), "level": level_top(), "dog_level": dog_level_top()}

    try:
        bot.edit_message_text(
            tops[data[1]], call.message.chat.id, call.message.id, reply_markup=markup
        )
    except ApiTelegramException:
        pass


@bot.callback_query_handler(lambda c: c.data.startswith("chest"))
def chest_callback(call: CallbackQuery):
    data = call.data.split(" ")

    if data[-1] != str(call.from_user.id):
        return

    if not isinstance(call.message, Message):
        return
    user = database.users.get(id=call.from_user.id)

    if data[1] == "open":
        key = get_or_add_user_item(user, "ключ")
        if key.quantity < 1:
            bot.answer_callback_query(call.id, "У тебя нет ключа", show_alert=True)
            return
        key.quantity -= 1
        mess = "Открыл сундук\n\n"
        items = []
        for _ in range(random.randint(2, 7)):
            rarity = random.choice(
                [
                    ItemRarity.COMMON,
                    ItemRarity.UNCOMMON,
                ]
            )
            quantity = get_item_count_for_rarity(rarity)
            item = random.choice(
                [
                    item
                    for item in items_list
                    if item.rarity == rarity and item.name != "бабло"
                ]
            )
            if item.name in items or quantity < 1:
                continue
            items.append(item.name)
            mess += f"+ {quantity} {item.name} {item.emoji}\n"
            user_item = get_or_add_user_item(user, item.name)
            user_item.quantity += quantity
            database.items.update(**user_item.to_dict())
        bot.delete_message(call.message.chat.id, call.message.id)
        if call.message.reply_to_message:
            bot.reply_to(call.message.reply_to_message, mess)
        else:
            bot.send_message(user.id, mess)
    elif data[1] == "leave":
        bot.delete_message(call.message.chat.id, call.message.id)
        if call.message.reply_to_message:
            bot.reply_to(call.message.reply_to_message, "*Ушел от сундука*")


@bot.callback_query_handler(lambda c: c.data.startswith("guide"))
def guide_callback(call: CallbackQuery):
    data = call.data.split(" ")

    if data[-1] != str(call.from_user.id):
        return

    main_markup = quick_markup(
        {
            "Для новичков ✨": {"callback_data": f"guide beginner {call.from_user.id}"},
            "Для продвинутых 🔫": {
                "callback_data": f"guide advanced {call.from_user.id}"
            },
            "Остальное 🧩": {"callback_data": f"guide other {call.from_user.id}"},
        },
        row_width=1,
    )
    main_mess = "Гайд по LiveBot 🍃"

    markup = InlineKeyboardMarkup(row_width=2)
    if data[1] in ["beginner", "advanced", "other"]:
        guide = toml.load(GUIDE_FILE_PATH)

        buttons = []

        for topic in guide[data[1]]:
            buttons.append(
                InlineKeyboardButton(
                    topic,
                    callback_data=f"guide {data[1]}_{topic.replace(' ', '-')} {call.from_user.id}",
                )
            )

        markup.add(*buttons)
        markup.row(
            InlineKeyboardButton(
                "Назад", callback_data=f"guide back {call.from_user.id}"
            )
        )
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=main_mess,
            reply_markup=markup,
        )
    elif "_" in data[1]:
        category, topic = data[1].split("_", 1)
        guide = toml.load(GUIDE_FILE_PATH)

        topic = topic.replace("-", " ")

        if category == "beginner":
            ru_category = "Для новичков"
        elif category == "advanced":
            ru_category = "Для продвинутых"
        elif category == "other":
            ru_category = "Остальное"

        text = (
            f"<code>{ru_category}</code> >> <code>{topic}</code>\n\n"
            f"<b>{topic.upper()}</b>\n\n"
            f"<i>{guide[category][topic]}</i>"
        )

        markup.row(
            InlineKeyboardButton(
                text="Назад", callback_data=f"guide {category} {call.from_user.id}"
            )
        )
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=text,
            reply_markup=markup,
        )
    elif data[1] == "back":
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=main_mess,
            reply_markup=main_markup,
        )


@bot.callback_query_handler(lambda c: c.data.startswith("actions"))
def actions_callback(call: CallbackQuery):
    data = call.data.split(" ")

    if data[-1] != str(call.from_user.id):
        return

    user = database.users.get(id=call.from_user.id)

    if data[1] == "choice":
        markup = InlineMarkup.actions_choice(user)

        mess = "Чем хочешь заняться?"

        bot.edit_message_text(
            mess, call.message.chat.id, call.message.id, reply_markup=markup
        )
    elif data[1] == "back":
        markup = InlineMarkup.home_main(user)
        mess = "🏠 Дом милый дом"
        bot.edit_message_text(
            mess, call.message.chat.id, call.message.id, reply_markup=markup
        )
    elif data[1] == "street":
        street(call, user)
    elif data[1] == "work":
        work(call, user)
    elif data[1] == "sleep":
        sleep(call, user)
    elif data[1] == "game":
        game(call, user)


@bot.callback_query_handler(lambda c: c.data.startswith("open"))
def open_callback(call: CallbackQuery):
    data = call.data.split(" ")

    if data[-1] != str(call.from_user.id):
        return

    user = database.users.get(id=call.from_user.id)

    if data[1] == "home":
        mess = "🏠 Дом милый дом"
        markup = InlineMarkup.home_main(user)
        bot.edit_message_text(
            mess, call.message.chat.id, call.message.id, reply_markup=markup
        )
    elif data[1] == "market-profile":
        mess = "Твой ларек"
        markup = InlineMarkup.market_profile(user)

        bot.edit_message_text(
            mess, call.message.chat.id, call.message.id, reply_markup=markup
        )


@bot.callback_query_handler(lambda c: c.data.split(" ")[0] == "market")
def market_callback(call: CallbackQuery):
    data = call.data.split(" ")

    if data[-1] != str(call.from_user.id):
        return

    user = database.users.get(id=call.from_user.id)

    if data[1] == "add":
        user_market_items_len = len(database.market_items.get_all(owner=user._id))
        if user_market_items_len >= user.max_items_count_in_market:
            bot.answer_callback_query(call.id, "Ты привисел лимит", show_alert=True)
            return
        from base.user_input.add_new_market_item import AddNewItemState

        user_items = sorted(
            database.items.get_all(owner=user._id),
            key=lambda i: i.quantity,
            reverse=True,
        )

        buttons = []
        for item in user_items:
            if item.quantity <= 0:
                continue

            buttons.append(
                InlineKeyboardButton(
                    f"{get_item_emoji(item.name)} {item.quantity}",
                    callback_data=f"sell {get_item(item.name).translit()} {user.id}",
                )
            )

        markup = InlineKeyboardMarkup(row_width=3)
        if len(buttons) == 0:
            bot.edit_message_text(
                "У тебя нет придметов для продажы",
                call.message.chat.id,
                call.message.id,
            )
            return

        markup.add(*buttons)

        bot.edit_message_text(
            "<b>Продажа придмета</b>\nВыбери придмет",
            call.message.chat.id,
            call.message.id,
            reply_markup=markup,
        )

        bot.set_state(user.id, AddNewItemState.name, call.message.chat.id)
    elif data[1] == "buy":
        try:
            market_item = database.market_items.get(_id=ObjectId(data[2]))
        except NoResult:
            bot.answer_callback_query(
                call.id,
                "Этот придмет либо уже купили либо владелец убрал с продажы",
                show_alert=True,
            )
            return

        item_owner = database.users.get(_id=market_item.owner)

        if item_owner.id == user.id:
            bot.answer_callback_query(
                call.id, "Сам у себя будешь покупать?", show_alert=True
            )
            return

        if market_item.price > user.coin:
            bot.answer_callback_query(call.id, "Тебе не хватает бабла", show_alert=True)
            return

        item_owner.coin += market_item.price
        user.coin -= market_item.price

        user_item = get_or_add_user_item(user, market_item.name)
        user_item.quantity += market_item.quantity

        database.items.update(**user_item.to_dict())
        database.users.update(**user.to_dict())
        database.users.update(**item_owner.to_dict())

        mess = f"{get_user_tag(user)} купил {market_item.quantity} {get_item_emoji(market_item.name)}"
        bot.send_message(call.message.chat.id, mess)

        bot.send_message(
            item_owner.id,
            f"{get_user_tag(user)} купил у тебя {market_item.quantity} {get_item_emoji(market_item.name)}",
        )

        database.market_items.delete(**market_item.to_dict())

        mess = "<b>Рынок</b>\n\n"
        market_items = database.market_items.get_all()
        markup = InlineMarkup.market_pager(user)
        mess += f"1 / {len(list(chunks(market_items, 6)))}"
        bot.edit_message_text(
            mess, call.message.chat.id, call.message.id, reply_markup=markup
        )
    elif data[1] == "view-my-items":
        markup = InlineMarkup.market_view_my_items(user)

        mess = "<b>Твои товары</b>"
        bot.edit_message_text(
            mess, call.message.chat.id, call.message.id, reply_markup=markup
        )
    elif data[1] == "delete":
        market_item = database.market_items.get(_id=ObjectId(data[2]))
        user_item = get_or_add_user_item(user, market_item.name)
        user_item.quantity += market_item.quantity
        database.items.update(**user_item.to_dict())
        database.market_items.delete(**market_item.to_dict())
        bot.answer_callback_query(call.id, "Придмет удален успешно", show_alert=True)
        markup = InlineMarkup.market_view_my_items(user)

        bot.edit_message_reply_markup(
            call.message.chat.id, call.message.id, reply_markup=markup
        )

    else:
        try:
            action = call.data.split(" ")[1]
            pos = int(call.data.split(" ")[2])

            market_items = database.market_items.get_all()
            max_pos = len(list(chunks(market_items, 6))) - 1

            if action == "next":
                pos += 1
            elif action == "back":
                pos -= 1
            elif action == "start":
                pos = 0
            elif action == "end":
                pos = max_pos

            if pos < 0 or pos > max_pos:
                raise IndexError

            mess = f"<b>Рынок</b>\n\n{pos + 1} / {max_pos + 1}"
            markup = InlineMarkup.market_pager(user=user, index=pos)

            bot.edit_message_text(
                mess, call.message.chat.id, call.message.id, reply_markup=markup
            )
        except (IndexError, ApiTelegramException):
            bot.answer_callback_query(call.id, "Дальше ничо нету", show_alert=True)


@bot.callback_query_handler(lambda c: c.data.startswith("market_item_open"))
def market_item_open_callback(call: CallbackQuery):
    data = call.data.split(" ")

    if data[-1] != str(call.from_user.id):
        return

    user = database.users.get(id=call.from_user.id)
    item_id = ObjectId(data[1])

    market_item = database.market_items.get(_id=item_id)

    item_owner = database.users.get(_id=market_item.owner)
    mess = (
        f"<b>{get_item_emoji(market_item.name)} {market_item.name} | {market_item.quantity} шт.</b>\n"
        f"Продавец: {get_user_tag(item_owner)}\n"
        f"Средный прайс: {get_middle_item_price(market_item.name)}/шт"
    )

    markup = InlineMarkup.market_item_open(user, market_item)
    bot.edit_message_text(
        mess, call.message.chat.id, call.message.id, reply_markup=markup
    )


@bot.callback_query_handler(lambda c: c.data.startswith("delate_state"), state="*")
def delate_state_callback(call: CallbackQuery):
    data = call.data.split(" ")

    if data[-1] != str(call.from_user.id):
        return

    if not bot.get_state(call.from_user.id, call.message.chat.id):
        bot.answer_callback_query(call.id, "Что отменять собрался?", show_alert=True)
        return

    bot.delete_state(call.from_user.id, call.message.chat.id)
    bot.delete_message(call.message.chat.id, call.message.id)
    bot.answer_callback_query(call.id, "Отменил")


@bot.callback_query_handler(lambda c: c.data.startswith("levelup"))
def levelup_callback(call: CallbackQuery):
    data = call.data.split(" ")

    if data[-1] != str(call.from_user.id):
        return

    user = database.users.get(id=call.from_user.id)

    if data[1] == "luck":
        user.luck += 1
    elif data[1] == "market":
        user.max_items_count_in_market += 1

    database.users.update(**user.to_dict())
    bot.answer_callback_query(call.id, "Поздравляю 🎉🎉", show_alert=True)
    bot.edit_message_reply_markup(
        call.message.chat.id, call.message.id, reply_markup=None
    )

