import random
from datetime import UTC, timedelta

from bson import ObjectId

from aiogram import F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    Message,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from base.actions import game, sleep, street, work
from base.items import ITEMS
from base.player import (
    add_user_usage_item,
    check_user_stats,
    coin_top,
    dog_level_top,
    generate_quest,
    get_available_items_for_use,
    get_or_add_user_item,
    level_top,
    use_item,
)


from database.funcs import database
from database.models import DogModel

from helpers.enums import ItemRarity, ItemType
from helpers.exceptions import ItemIsCoin, NoResult
from helpers.markups import InlineMarkup
from helpers.utils import (
    achievement_progress,
    check_user_subscription,
    batched,
    get_achievement,
    get_item,
    get_item_count_for_rarity,
    get_item_emoji,
    get_middle_item_price,
    get_time_difference_string,
    get_user_tag,
    increment_achievement_progress,
    quick_markup,
    safe,
    utcnow,
)

router = Router()


@router.callback_query(F.data.startswith("dog"))
async def dog_callback(call: CallbackQuery):
    data = call.data.split(" ")
    user = database.users.get(id=call.from_user.id)

    try:
        dog = database.dogs.get(owner=user._id)
    except NoResult:
        dog = None

    if not isinstance(call.message, Message):
        return

    if data[-1] != str(user.id):
        return
    if data[1] == "leave":
        await call.message.delete()
        await call.message.answer_sticker(
            "CAACAgIAAxkBAAEpvztl21ybsmS9RVqaYhV8ZtA353n4HgACJwEAAjDUnRGOYUDc7Hyw5TQE",
        )

        await call.message.answer("Прогнал бедную собачку(")
        return
    if data[1] == "friend":
        date = call.message.date.astimezone(UTC)
        current_time = utcnow()
        time_difference = current_time - date

        if time_difference >= timedelta(minutes=1):
            await call.message.delete()
            await call.answer("Пока ты думал псина сбежала", show_alert=True)
            return

        item = get_or_add_user_item(user, "кость")

        if item.quantity <= int(data[2]):
            await call.answer(
                f"Тебе не хватает 🦴, нужно {data[2]} а у тебя {item.quantity}", show_alert=True
            )
            return

        dog = DogModel(owner=user._id)
        dog.name = f"Собачка-{user.id}"
        database.dogs.add(**dog.to_dict())

        await call.message.delete()
        await call.message.answer_sticker(
            "CAACAgIAAxkBAAEpvz9l211Kyfi280mwFR6XMKUhzMXbiwACGAEAAjDUnREiQ2-IziTqFTQE"
        )

        await call.message.answer(
            "Завел собачку 🐶\n\nНапиши /rename_dog [имя] чтобы дать имя пёсику",
        )
        return
    if data[1] == "feed" and dog:
        if dog.hunger == 0:
            await call.answer(f"{dog.name} не голоден", show_alert=True)
            return
        item = get_or_add_user_item(user, "мясо")

        quantity = dog.level * 2

        if item.quantity < quantity:
            await call.answer(
                f"Тебе не хватает мяса, нужно {quantity} а у тебя {item.quantity}",
                show_alert=True,
            )
            return
        item.quantity -= quantity
        count = random.randint(1, 10)
        dog.hunger -= count
        dog.xp += random.uniform(0.1, 0.3)
        await call.answer(
            f"{dog.name} поел мяса и восстановил {count} единиц голода",
            show_alert=True,
        )
        database.dogs.update(**dog.to_dict())
        database.items.update(**item.to_dict())

        await check_user_stats(user, call.message.chat.id)

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

        await call.message.edit_text(mess, reply_markup=markup)
    if data[1] == "sleep" and dog:
        current_time = utcnow()
        time_difference = current_time - dog.sleep_time
        if time_difference <= timedelta(minutes=1):
            time_difference = get_time_difference_string(time_difference - timedelta(minutes=1))
            await call.answer(
                f"{dog.name} спит, жди {time_difference}",
                show_alert=True,
            )
            return

        dog.sleep_time = utcnow()

        time_difference = get_time_difference_string(
            (current_time - dog.sleep_time) - timedelta(hours=1)
        )

        await call.answer(
            f"{dog.name} пошел спать, проснется через {time_difference}",
            show_alert=True,
        )

    if data[1] == "wakeup" and dog:
        await call.answer(f"{dog.name} проснулся", show_alert=True)
        dog.sleep_time = utcnow()

    database.users.update(**user.to_dict())
    if dog:
        database.dogs.update(**dog.to_dict())
    await check_user_stats(user)


@router.callback_query(F.data.startswith("skip_quest"))
async def new_quest_callback(call: CallbackQuery):
    if call.data.split(" ")[-1] != str(call.from_user.id):
        return

    if not isinstance(call.message, Message):
        return

    user = database.users.get(id=call.from_user.id)

    if not user.new_quest_coin_quantity:
        user.new_quest_coin_quantity = 2

    if user.new_quest_coin_quantity > user.coin:
        await call.answer(
            (
                "У тебя недостаточно бабла."
                f"Чтобы получить новый квест надо иметь {user.new_quest_coin_quantity}"
            ),
            show_alert=True,
        )
        return

    generate_quest(user)
    user.coin -= user.new_quest_coin_quantity
    user.new_quest_coin_quantity += random.randint(10, 20)
    database.users.update(**user.to_dict())

    await call.answer(
        "Ты получил новый квест, напиши /quest чтобы посмотреть",
        show_alert=True,
    )


@router.callback_query(F.data.startswith("finish_quest"))
async def finish_quest_callback(call: CallbackQuery):
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
        await call.answer("Кудааа, тебе не хватает", show_alert=True)  # cspell:ignore Кудааа
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

    total_time = utcnow() - quest.start_time
    mess += get_time_difference_string(total_time)

    generate_quest(user)
    await call.message.delete()

    user_message = call.message.reply_to_message
    await call.message.answer_sticker(
        "CAACAgIAAxkBAAEpslFl2JwAAaZFMa3RM-3fKaHU7RYrOSQAAoIPAAJ73EFKS4aLwGmJ_Ok0BA",
    )  # cspell:disable-line  # pylint: disable=line-too-long
    if user_message:
        await user_message.reply(mess)
    else:
        await call.message.answer(mess)

    await check_user_stats(user, call.message.chat.id)


@router.callback_query(F.data.startswith("use"))
async def use_callback(call: CallbackQuery):
    if call.data.split(" ")[-1] != str(call.from_user.id):
        return

    user = database.users.get(id=call.from_user.id)

    item = get_item(call.data.split(" ")[1])

    if not call.message.reply_to_message:
        return

    await use_item(call.message.reply_to_message, item.name)

    markup = InlineMarkup.use(user)

    items = get_available_items_for_use(user)

    if not items:
        mess = "Нет доступных предметов для юза"
        await call.message.edit_text(mess)

    await call.message.edit_reply_markup(reply_markup=markup)


@router.callback_query(F.data.startswith("item_info_main"))
async def item_info_main_callback(call: CallbackQuery):
    if call.data.split(" ")[-1] != str(call.from_user.id):
        return

    try:
        user = database.users.get(id=call.from_user.id)
        action = call.data.split(" ")[1]
        pos = int(call.data.split(" ")[2])
        max_pos = len(list(batched(ITEMS, 6))) - 1

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

        await call.message.edit_text(mess, reply_markup=markup)
    except (IndexError, TelegramAPIError):
        await call.answer("Дальше ничо нету", show_alert=True)


@router.callback_query(F.data.startswith("item_info"))
async def item_info_callback(call: CallbackQuery):
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
            [f"{get_item_emoji(name)} {name} {count}" for name, count in item.craft.items()]
        )

    mess = (
        f"<b>{item.emoji} {item.name}</b>\n\n"
        f"<b>Редкость:</b> {item.rarity.value}\n\n"
        f"<b>Описание:</b> <i>{item.desc}</i>\n\n"
        + (f"<b>Крафт:</b> <i>{craft}</i>\n" if item.craft else "")
    )

    await call.message.edit_text(mess, reply_markup=markup)


@router.callback_query(F.data.startswith("trader"))
async def trader_callback(call: CallbackQuery):
    data = call.data.split(" ")
    if data[-1] != str(call.from_user.id):
        return

    if not isinstance(call.message, Message):
        return
    user = database.users.get(id=call.from_user.id)

    if data[1] == "leave":
        await call.message.delete()
        await call.message.answer_sticker(
            "CAACAgEAAxkBAAEpxYVl3KqB7JnvbmYgXQqVAhUQYbnyXwACngIAAv9iMUeUcUiHcCrhSTQE",
        )
        await call.message.answer("Пф... не хочешь как хочешь")

    elif data[1] == "trade":
        item = get_item(data[2])
        quantity = int(data[3])
        price = int(data[4])
        user_item = get_or_add_user_item(user, item.name)

        if user.coin < price:
            await call.answer(f"Тебе нехватает {price - user.coin} бабла", show_alert=True)

            return

        user.coin -= price
        user_item.quantity += quantity
        await call.mesage.delete()
        await call.message.answer(f"Купил {quantity} {item.name} {item.emoji} за {price}")


@router.callback_query(F.data.startswith("top"))
async def top_callback(call: CallbackQuery):
    data = call.data.split(" ")
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
        await call.message.edit_text(tops[data[1]], reply_markup=markup)
    except TelegramAPIError:
        pass


@router.callback_query(F.data.startswith("chest"))
async def chest_callback(call: CallbackQuery):
    data = call.data.split(" ")

    if data[-1] != str(call.from_user.id):
        return

    if not isinstance(call.message, Message):
        return
    user = database.users.get(id=call.from_user.id)

    if data[1] == "open":
        key = get_or_add_user_item(user, "ключ")
        if key.quantity < 1:
            await call.answer("У тебя нет ключа", show_alert=True)
            return
        key.quantity -= 1
        mess = "Открыл сундук\n\n"
        items = []
        for _ in range(random.randint(2, 5)):
            rarity = random.choice(
                [
                    ItemRarity.COMMON,
                    ItemRarity.UNCOMMON,
                ]
            )
            quantity = get_item_count_for_rarity(rarity)
            item = random.choice(
                [item for item in ITEMS if item.rarity == rarity and item.name != "бабло"]
            )
            if item.name in items or quantity < 1:
                continue
            items.append(item.name)
            mess += f"+ {quantity} {item.name} {item.emoji}\n"
            user_item = get_or_add_user_item(user, item.name)
            user_item.quantity += quantity
            database.items.update(**user_item.to_dict())
        increment_achievement_progress(user, "сундук-собиратель")
        await call.message.delete()
        if call.message.reply_to_message:
            await call.message.reply(mess)
        else:
            await call.bot.send_message(user.id, mess)

    elif data[1] == "leave":
        await call.message.delete()
        if call.message.reply_to_message:
            await call.message.reply("*Ушел от сундука*")


@router.callback_query(F.data.startswith("actions"))
async def actions_callback(call: CallbackQuery):
    data = call.data.split(" ")

    if data[-1] != str(call.from_user.id):
        return

    user = database.users.get(id=call.from_user.id)

    if data[1] == "choice":
        markup = InlineMarkup.actions_choice(user)

        mess = "Чем хочешь заняться?"

        await call.message.edit_text(mess, reply_markup=markup)
    elif data[1] == "back":
        markup = InlineMarkup.home_main(user)
        mess = "🏠 Дом милый дом"
        await call.message.edit_text(mess, reply_markup=markup)
    elif data[1] == "street":
        await street(call, user)
    elif data[1] == "work":
        await work(call, user)
    elif data[1] == "sleep":
        await sleep(call, user)
    elif data[1] == "game":
        await game(call, user)


@router.callback_query(F.data.startswith("open"))
async def open_callback(call: CallbackQuery):
    data = call.data.split(" ")

    if data[-1] != str(call.from_user.id):
        return

    user = database.users.get(id=call.from_user.id)

    if data[1] == "home":
        mess = "🏠 Дом милый дом"
        markup = InlineMarkup.home_main(user)
        await call.message.edit_text(mess, reply_markup=markup)
    elif data[1] == "market-profile":
        mess = "Твой ларек"
        markup = InlineMarkup.market_profile(user)

        await call.message.edit_text(mess, reply_markup=markup)
    elif data[1] == "bag":
        mess = "Инвентарь"
        markup = InlineMarkup.bag(user)

        await call.message.edit_text(mess, reply_markup=markup)


@router.callback_query(F.data.startswith("market"))
async def market_callback(call: CallbackQuery, state: FSMContext):
    data = call.data.split(" ")

    if data[-1] != str(call.from_user.id):
        return

    user = database.users.get(id=call.from_user.id)

    if data[1] == "add":
        user_market_items_len = len(database.market_items.get_all(owner=user._id))
        if user_market_items_len >= user.max_items_count_in_market:
            await call.answer("Ты привесил лимит", show_alert=True)
            return
        from base.user_input.add_new_market_item import AddNewItemState

        user_items = sorted(
            database.items.get_all(owner=user._id),
            key=lambda i: i.quantity,
            reverse=True,
        )

        buttons = []
        for item in user_items:
            if item.quantity <= 0 or get_item(item.name).type == ItemType.USABLE:
                continue

            buttons.append(
                InlineKeyboardButton(
                    text=f"{get_item_emoji(item.name)} {item.quantity}",
                    callback_data=f"sell {get_item(item.name).translit()} {user.id}",
                )
            )

        builder = InlineKeyboardBuilder()
        if len(buttons) == 0:
            await call.message.edit_text("У тебя нет предметов для продажи")
            return

        builder.add(*buttons)
        await call.message.edit_text(
            "<b>Продажа предмета</b>\nВыбери предмет", reply_markup=builder.as_markup()
        )

        await state.set_state(AddNewItemState.name)
    elif data[1] == "buy":
        try:
            market_item = database.market_items.get(_id=ObjectId(data[2]))
        except NoResult:
            await call.answer(
                "Этот предмет либо уже купили либо владелец убрал с продажи", show_alert=True
            )
            return

        item_owner = database.users.get(_id=market_item.owner)

        if item_owner.id == user.id:
            await call.answer("Сам у себя будешь покупать?", show_alert=True)
            return

        if market_item.price > user.coin:
            await call.answer("Тебе не хватает бабла", show_alert=True)
            return

        item = get_item(market_item.name)

        item_owner.coin += market_item.price
        user.coin -= market_item.price
        if item.type == ItemType.COUNTABLE:
            user_item = get_or_add_user_item(user, market_item.name)
            user_item.quantity += market_item.quantity
        else:
            user_item = add_user_usage_item(
                user,
                market_item.name,
                market_item.usage,  # type: ignore
            )
            user_item.quantity = market_item.quantity

        database.items.update(**user_item.to_dict())
        database.users.update(**user.to_dict())
        database.users.update(**item_owner.to_dict())
        database.market_items.delete(**market_item.to_dict())

        increment_achievement_progress(user, "богач", market_item.price)
        increment_achievement_progress(item_owner, "продавец")

        usage = f" ({int(market_item.usage)}%)" if market_item.usage else ""
        emoji = get_item_emoji(market_item.name)
        mess = f"{get_user_tag(user)} купил {market_item.quantity} {emoji}{usage}"
        await safe(call.message.answer(mess))

        await safe(
            call.bot.send_message(
                item_owner.id,
                f"{get_user_tag(user)} купил у тебя {market_item.quantity} {emoji}{usage}",
            )
        )

        mess = "<b>Рынок</b>\n\n"
        market_items = database.market_items.get_all()
        markup = InlineMarkup.market_pager(user)
        mess += f"1 / {len(list(batched(market_items, 6)))}"
        await call.message.edit_text(
            mess,
            reply_markup=markup,
        )
    elif data[1] == "view-my-items":
        markup = InlineMarkup.market_view_my_items(user)

        mess = "<b>Твои товары</b>"
        await call.message.edit_text(
            mess,
            reply_markup=markup,
        )
    elif data[1] == "delete":
        market_item = database.market_items.get(_id=ObjectId(data[2]))
        user_item = get_or_add_user_item(user, market_item.name)
        user_item.quantity += market_item.quantity
        database.items.update(**user_item.to_dict())
        database.market_items.delete(**market_item.to_dict())
        await call.answer(
            "предмет удален успешно",
            show_alert=True,
        )
        markup = InlineMarkup.market_view_my_items(user)

        await call.message.edit_reply_markup(
            reply_markup=markup,
        )

    else:
        try:
            action = call.data.split(" ")[1]
            pos = int(call.data.split(" ")[2])

            market_items = database.market_items.get_all()
            max_pos = len(list(batched(market_items, 6))) - 1

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

            await call.message.edit_text(mess, reply_markup=markup)
        except (IndexError, TelegramAPIError):
            await call.answer("Дальше ничо нету", show_alert=True)


@router.callback_query(F.data.startswith("market_item_open"))
async def market_item_open_callback(call: CallbackQuery):
    data = call.data.split(" ")

    if data[-1] != str(call.from_user.id):
        return

    user = database.users.get(id=call.from_user.id)
    item_id = ObjectId(data[1])

    market_item = database.market_items.get(_id=item_id)

    item_owner = database.users.get(_id=market_item.owner)
    emoji = get_item_emoji(market_item.name)
    mess = (
        f"<b>{emoji} {market_item.name} | {market_item.quantity} шт.</b>\n"
        f"Продавец: {get_user_tag(item_owner)}\n"
        f"Средней прайс: {get_middle_item_price(market_item.name)}/шт"
    )

    markup = InlineMarkup.market_item_open(user, market_item)
    await call.message.edit_text(mess, reply_markup=markup)


@router.callback_query(F.data.startswith("delate_state"), StateFilter("*"))
async def delate_state_callback(call: CallbackQuery, state: FSMContext):
    data = call.data.split(" ")

    if data[-1] != str(call.from_user.id):
        return

    if not await state.get_state():
        await call.answer("Что отменять собрался?", show_alert=True)
        return
    await state.delete()
    if call.message.id:
        await call.message.delete()
    await call.answer("Отменил")


@router.callback_query(F.data.startswith("levelup"))
async def levelup_callback(call: CallbackQuery):
    data = call.data.split(" ")

    if data[-1] != str(call.from_user.id):
        return

    user = database.users.get(id=call.from_user.id)

    if data[1] == "luck":
        user.luck += 1
    elif data[1] == "market":
        user.max_items_count_in_market += 1

    database.users.update(**user.to_dict())
    await call.answer("Поздравляю 🎉🎉", show_alert=True)
    await call.message.edit_reply_markup(reply_markup=None)


@router.callback_query(F.data.startswith("daily_gift"))
async def daily_gift_callback(call: CallbackQuery):
    data = call.data.split(" ")

    if data[-1] != str(call.from_user.id):
        return

    user = database.users.get(id=call.from_user.id)

    if data[1] == "claim":
        if not check_user_subscription(user):
            await call.answer(
                "Чтобы использовать эту функцию нужно подписаться на новостной канал",
                show_alert=True,
            )
            return
        now = utcnow()

        daily_gift = database.daily_gifts.get(owner=user._id)
        if daily_gift.is_claimed:
            time_difference = get_time_difference_string(daily_gift.next_claimable_at - now)
            await call.answer(
                f"Ты сегодня уже получил подарок. Жди {time_difference}",
                show_alert=True,
            )
            markup = InlineMarkup.daily_gift(user, daily_gift)
            await call.message.edit_message_reply_markup(reply_markup=markup)
            return

        if not daily_gift.last_claimed_at:
            daily_gift.last_claimed_at = now

        if daily_gift.last_claimed_at.date() == (now - timedelta(days=1)).date():
            daily_gift.streak += 1
        else:
            daily_gift.streak = 1

        daily_gift.last_claimed_at = now
        daily_gift.next_claimable_at = now + timedelta(days=1)
        daily_gift.is_claimed = True
        database.daily_gifts.update(**daily_gift.to_dict())

        mess = f"<b>{get_user_tag(user)} получил ежедневный подарок</b>\n\n"
        for item_name in daily_gift.items:
            item = get_item(item_name)
            quantity = get_item_count_for_rarity(item.rarity)
            try:
                user_item = get_or_add_user_item(user, item.name)
                user_item.quantity += quantity
                database.items.update(**user_item.to_dict())
            except ItemIsCoin:
                user.coin += quantity
            mess += f"+{quantity} {item.name} {item.emoji}\n"

        markup = InlineMarkup.daily_gift(user, daily_gift)
        await call.message.edit_message_reply_markup(reply_markup=markup)
        await call.message.answer(mess)


@router.callback_query(F.data.startswith("transfer"))
async def transfer_callback(call: CallbackQuery):
    data = call.data.split(" ")

    if data[-1] != str(call.from_user.id):
        return

    user = database.users.get(id=call.from_user.id)
    reply_user = database.users.get(id=int(data[-2]))

    item = database.items.get(_id=ObjectId(data[1]))

    if item.quantity <= 0:
        await call.answer("У тебя нет такого предмета")
        return

    item.owner = reply_user._id

    database.items.update(**item.to_dict())
    mess = (
        f"{user.name} подарил {reply_user.name}\n"
        "----------------\n"
        f"{get_item_emoji(item.name)} {item.name} ({int(item.usage)}%)"  # type: ignore
    )

    database.users.update(**user.to_dict())
    database.users.update(**reply_user.to_dict())

    await call.message.answer(mess)


@router.callback_query(F.data.startswith("achievements"))
async def achievements_callback(call: CallbackQuery):
    data = call.data.split(" ")

    if data[-1] != str(call.from_user.id):
        return

    user = database.users.get(id=call.from_user.id)

    if data[1] == "view":
        ach = get_achievement(data[2])
        mess = f"<b>{ach.emoji} {ach.name}</b>\n\n"
        mess += f"<i>{ach.desc}</i>\n\n"
        mess += f"{achievement_progress(user, ach.name)}"

        markup = quick_markup({"Назад": {"callback_data": f"achievements main {user.id}"}})

        await call.message.edit_text(mess, reply_markup=markup)
    elif data[1] == "main":
        mess = "Достижения"

        markup = InlineMarkup.achievements(user)

        await call.message.edit_text(mess, reply_markup=markup)

    elif data[1] == "filter":
        filter = data[2]
        markup = InlineMarkup.achievements_view(user, filter)  # type: ignore

        await call.message.edit_message_reply_markup(reply_markup=markup)


@router.callback_query(F.data.startswith("accept_rules"))
async def accept_rules_callback(call: CallbackQuery):
    data = call.data.split(" ")

    if data[-1] != str(call.from_user.id):
        return

    user = database.users.get(id=call.from_user.id)
    user.accepted_rules = True
    database.users.update(**user.to_dict())

    await call.answer(
        "Теперь можешь спокойно пользовался ботом",
        show_alert=True,
    )

    await call.message.delete()  # type: ignore


@router.callback_query(F.data.startswith("event_shop"))
async def event_shop_callback(call: CallbackQuery):
    data = call.data.split(" ")

    if data[-1] != str(call.from_user.id):
        return

    if data[1] != "buy":
        return

    user = database.users.get(id=call.from_user.id)

    candy = get_or_add_user_item(user, "конфета")

    item = get_item(data[2])
    quantity = int(data[3])

    if candy.quantity < quantity:
        await call.answer("Недостаточно конфет", show_alert=True)
        return

    user_item = get_or_add_user_item(user, item.name)
    user_item.quantity += 1
    candy.quantity -= quantity

    database.items.update(**user_item.to_dict())
    database.items.update(**candy.to_dict())

    mess = "<b>Ивентовый магазин</b>\n\n"
    mess += f"У тебя {candy.quantity} {get_item_emoji(candy.name)}"

    markup = InlineMarkup.event_shop(user)

    await call.message.edit_text(mess, reply_markup=markup)

    await call.answer(
        f"Ты купил 1 {item.emoji} за {quantity} {get_item_emoji(candy.name)}",
        show_alert=True,
    )
