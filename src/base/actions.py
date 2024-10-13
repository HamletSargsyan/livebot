from datetime import timedelta
import random
from telebot.types import CallbackQuery

from base.mobs import generate_mob
from base.weather import get_weather
from base.player import check_user_stats, get_or_add_user_item

from database.funcs import database
from database.models import UserAction, UserModel

from config import bot

from helpers.exceptions import NoResult
from helpers.markups import InlineMarkup
from helpers.utils import (
    get_item_emoji,
    get_time_difference_string,
    increment_achievement_progress,
    utcnow,
)


def street(call: CallbackQuery, user: UserModel):
    try:
        dog = database.dogs.get(**{"owner": user._id})
    except NoResult:
        dog = None

    if user.hunger >= 80:
        bot.answer_callback_query(
            call.id, "Ты слишком голодный для прогулки", show_alert=True
        )
        return
    elif user.fatigue >= 85:
        bot.answer_callback_query(
            call.id, "Ты слишком устал для прогулки", show_alert=True
        )
        return

    current_time = utcnow()

    if user.action is None:
        user.action = UserAction("street", current_time + timedelta(hours=1))
        database.users.update(**user.to_dict())
    elif user.action.type != "street":
        bot.answer_callback_query(call.id, "Ты занят чем то другим", show_alert=True)
        return

    if user.action.end >= current_time:
        time_left = user.action.end - current_time
        mess = f"<b>Улица</b>\n\nГуляешь\nОсталось: {get_time_difference_string(time_left)}"

        walk_duration = current_time - user.action.start
        if not user.met_mob and walk_duration >= timedelta(
            minutes=random.randint(15, 20)
        ):
            mob = generate_mob()
            if mob:
                mob.init(user, call.message)
                if dog and mob.name == "псина":
                    bot.edit_message_text(
                        mess,
                        call.message.chat.id,
                        call.message.id,
                        reply_markup=InlineMarkup.update_action(user, "street"),
                    )
                    return
                user.met_mob = True

                database.users.update(**user.to_dict())
                mob.on_meet()
                return

            bot.edit_message_text(
                mess,
                call.message.chat.id,
                call.message.id,
                reply_markup=InlineMarkup.update_action(user, "street"),
            )
            return
        bot.edit_message_text(
            mess,
            call.message.chat.id,
            call.message.id,
            reply_markup=InlineMarkup.update_action(user, "street"),
        )
        return

    weather = get_weather()

    snow = 2
    water = 2
    if weather.main.temp <= -15:
        snow = 10
    elif weather.main.temp <= -5:
        snow = 5

    if weather.weather.main == "Snow":
        snow *= 3
    elif weather.weather.main == "Rain":
        water *= 3

    loot_table = [
        ["бабло", (1, 50)],
        ["трава", (1, 3)],
        ["гриб", (1, 3)],
        ["вода", (2 * water, 3 * water)],
        ["чаинка", (1, 3)],
        ["бабочка", (5, 10)],
    ]

    if weather.main.temp < 0:
        loot_table.append(["снежок", (10 * snow, 20 * snow)])

    xp = random.uniform(3.0, 5.0)
    loot = False
    mess = "Ты прогулялся\n\n"
    for _ in range(random.randint(1, len(loot_table))):
        item_ = random.choice(loot_table)
        quantity = random.randint(item_[1][0], item_[1][1])

        if quantity > 0:
            loot = True
            if random.randint(1, user.luck) + 50 < user.luck:
                quantity += random.randint(10, 20)

            mess += f"+ {quantity} {item_[0]} {get_item_emoji(item_[0])}\n"
            if item_[0] == "бабло":
                user.coin += quantity
                database.users.update(**user.to_dict())
            else:
                user_item = get_or_add_user_item(user, item_[0])
                user_item.quantity += quantity
                database.items.update(**user_item.to_dict())

    if dog:
        dog.hunger += random.randint(0, 5)
        # dog.fatigue += random.randint(0, 10)
        dog.xp += random.uniform(1.5, 2.5)
        database.dogs.update(**dog.to_dict())

    user.xp += xp
    user.action = None

    user.hunger += random.randint(2, 5)
    user.fatigue += random.randint(3, 8)
    user.mood -= random.randint(3, 6)
    user.met_mob = False
    database.users.update(**user.to_dict())
    increment_achievement_progress(user, "бродяга")

    try:
        user_notification = database.notifications.get(**{"owner": user._id})
        user_notification.walk = False
        database.notifications.update(**user_notification.to_dict())
    except NoResult:
        pass

    if not loot:
        bot.edit_message_text(mess, call.message.chat.id, call.message.id)
        return

    bot.edit_message_text(mess, call.message.chat.id, call.message.id)
    check_user_stats(user, call.message.chat.id)


def work(call: CallbackQuery, user: UserModel):
    if user.hunger >= 80:
        bot.answer_callback_query(
            call.id, "Ты слишком голодный для работы", show_alert=True
        )
        return
    elif user.fatigue >= 85:
        bot.answer_callback_query(
            call.id, "Ты слишком устал для работы", show_alert=True
        )
        return

    current_time = utcnow()

    if user.action is None:
        user.action = UserAction("work", current_time + timedelta(hours=3))
        database.users.update(**user.to_dict())
    elif user.action.type != "work":
        bot.answer_callback_query(call.id, "Ты занят чем то другим", show_alert=True)
        return

    if user.action.end >= current_time:
        time_left = user.action.end - current_time
        mess = f"<b>Работа</b>\n\nОсталось: {get_time_difference_string(time_left)}"

        bot.edit_message_text(
            mess,
            call.message.chat.id,
            call.message.id,
            reply_markup=InlineMarkup.update_action(user, "work"),
        )
        return

    xp = random.uniform(5.0, 20.0)
    coin = random.randint(100, 200) * user.level
    if random.randint(1, 100) < user.luck:
        coin *= 2
        xp += random.uniform(5.0, 7.5)

    mess = f"Закончил работу\n\n" f"+ {coin} бабло {get_item_emoji('бабло')}"

    user.coin += coin

    user.xp += xp
    user.action = None

    user.fatigue += random.randint(5, 10)
    user.hunger += random.randint(3, 6)
    user.mood -= random.randint(3, 6)

    database.users.update(**user.to_dict())
    increment_achievement_progress(user, "работяга")

    try:
        user_notification = database.notifications.get(**{"owner": user._id})
        user_notification.work = False
        database.notifications.update(**user_notification.to_dict())
    except NoResult:
        pass
    bot.edit_message_text(mess, call.message.chat.id, call.message.id)
    check_user_stats(user, call.message.chat.id)


def sleep(call: CallbackQuery, user: UserModel):
    current_time = utcnow()

    if user.action is None:
        user.action = UserAction(
            "sleep", current_time + timedelta(hours=random.randint(3, 8))
        )
        database.users.update(**user.to_dict())
    elif user.action.type != "sleep":
        bot.answer_callback_query(call.id, "Ты занят чем то другим", show_alert=True)
        return

    if user.action.end >= current_time:
        time_left = user.action.end - current_time
        mess = f"<b>🛏️ Спишь</b>\n\nОсталось: {get_time_difference_string(time_left)}"

        bot.edit_message_text(
            mess,
            call.message.chat.id,
            call.message.id,
            reply_markup=InlineMarkup.update_action(user, "sleep"),
        )
        return

    fatigue = random.randint(50, 100)
    user.fatigue -= fatigue
    user.xp += random.uniform(1.5, 2.0)
    user.action = None

    database.users.update(**user.to_dict())
    increment_achievement_progress(user, "сонный")

    mess = "Охх, хорошенько поспал"
    bot.edit_message_text(mess, call.message.chat.id, call.message.id)
    check_user_stats(user, call.message.chat.id)


def game(call: CallbackQuery, user: UserModel):
    current_time = utcnow()

    if user.level < 3:
        bot.answer_callback_query(call.id, "Доступно с 3 лвла", show_alert=True)
        return

    if user.action is None:
        user.action = UserAction(
            "game",
            current_time
            + timedelta(hours=random.randint(0, 3), minutes=random.randint(15, 20)),
        )

        database.users.update(**user.to_dict())
    elif user.action.type != "game":
        bot.answer_callback_query(call.id, "Ты занят чем то другим", show_alert=True)
        return

    if user.action.end >= current_time:
        time_left = user.action.end - current_time
        mess = f"<b>🎮 Играешь</b>\n\nОсталось: {get_time_difference_string(time_left)}"

        bot.edit_message_text(
            mess,
            call.message.chat.id,
            call.message.id,
            reply_markup=InlineMarkup.update_action(user, "sleep"),
        )
        return

    user.fatigue += random.randint(0, 10)
    user.xp += random.uniform(3.5, 5.7)
    user.mood += random.randint(5, 10)
    if random.randint(1, 100) < user.luck:
        user.mood *= 2
    user.action = None

    database.users.update(**user.to_dict())
    increment_achievement_progress(user, "игроман")

    mess = "Как же хорошо было играть 😊"
    bot.edit_message_text(mess, call.message.chat.id, call.message.id)
    check_user_stats(user, call.message.chat.id)
