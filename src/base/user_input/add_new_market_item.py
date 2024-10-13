# pyright: reportOptionalContextManager=none

from telebot.types import Message, CallbackQuery
from telebot.handler_backends import State, StatesGroup


from config import bot
from helpers.enums import ItemType
from helpers.utils import (
    from_user,
    get_item,
    get_item_emoji,
    get_middle_item_price,
    get_user_tag,
)
from database.funcs import database, redis_cache
from database.models import MarketItemModel
from helpers.exceptions import NoResult
from helpers.markups import InlineMarkup


class AddNewItemState(StatesGroup):
    name = State()
    item_oid = State()
    quantity = State()
    price = State()


@bot.callback_query_handler(
    state=AddNewItemState.name, func=lambda c: c.data.startswith("sell")
)
def name_state(call: CallbackQuery):
    data = call.data.split(" ")

    if data[-1] != str(call.from_user.id):
        return

    item = get_item(data[1])

    if item.type == ItemType.USABLE:
        bot.answer_callback_query(
            call.id,
            "Этот предмет нельзя продавать (https://github.com/HamletSargsyan/livebot/issues/41)",
        )
        return

    with bot.retrieve_data(call.from_user.id, call.message.chat.id) as data:  # type: ignore
        data["name"] = item.name

    user = database.users.get(id=call.from_user.id)
    user_item = database.items.get(name=item.name, owner=user._id)

    markup = InlineMarkup.delate_state(user)
    bot.edit_message_text(
        f"<b>Продажа предмета {item.emoji}</b>\nВведи кол-во ({user_item.quantity})",
        call.message.chat.id,
        call.message.id,
        reply_markup=markup,
    )
    bot.set_state(call.from_user.id, AddNewItemState.quantity, call.message.chat.id)

    redis_cache.setex(f"{user.id}_item_add_message", 300, call.message.id)  # type: ignore


# TODO
@bot.message_handler(state=AddNewItemState.item_oid, is_digit=True)
def select_item_state(message: Message): ...


@bot.message_handler(
    state=[AddNewItemState.quantity, AddNewItemState.price], is_digit=False
)
def invalid_int_input(message: Message):
    user = database.users.get(id=from_user(message).id)
    markup = InlineMarkup.delate_state(user)
    bot.reply_to(message, "Введите число", reply_markup=markup)


@bot.message_handler(state=AddNewItemState.quantity, is_digit=True)
def quantity_state(message: Message):
    user = database.users.get(id=from_user(message).id)
    with bot.retrieve_data(from_user(message).id, message.chat.id) as data:  # type: ignore
        user_item = database.items.get(owner=user._id, name=data["name"])

    if user_item.quantity < int(message.text):  # type: ignore
        bot.reply_to(message, "У тебя нет столько")
        return

    with bot.retrieve_data(from_user(message).id, message.chat.id) as data:  # type: ignore
        data["quantity"] = int(message.text)  # type: ignore

    call_message_id = redis_cache.get(f"{from_user(message).id}_item_add_message")
    bot.delete_message(message.chat.id, message.id)

    item = get_item(user_item.name)
    markup = InlineMarkup.delate_state(user)
    bot.edit_message_text(
        f"<b>Продажа предмета {item.emoji}</b>\nВведи прайс (+-{get_middle_item_price(item.name)}/шт)",
        message.chat.id,
        call_message_id,  # type: ignore
        reply_markup=markup,
    )
    bot.set_state(from_user(message).id, AddNewItemState.price, message.chat.id)


@bot.message_handler(state=AddNewItemState.price, is_digit=True)
def price_state(message: Message):
    user = database.users.get(id=from_user(message).id)
    with bot.retrieve_data(from_user(message).id, message.chat.id) as data:  # type: ignore
        try:
            user_item = database.items.get(owner=user._id, name=data["name"])
        except NoResult:
            bot.reply_to(message, "У тебя нет такого предмета")
            return

        if user_item.quantity < data["quantity"]:
            bot.reply_to(message, "У тебя нет столько")
            return

        item = MarketItemModel(
            name=data["name"].lower(),
            quantity=int(data["quantity"]),
            price=int(message.text),  # type: ignore
            owner=user._id,
        )

    bot.delete_state(user.id, message.chat.id)
    database.market_items.add(**item.to_dict())
    user_item.quantity -= item.quantity
    database.items.update(**user_item.to_dict())

    call_message_id = redis_cache.get(f"{from_user(message).id}_item_add_message")

    bot.delete_message(message.chat.id, call_message_id)  # type: ignore
    bot.delete_message(message.chat.id, message.id)

    redis_cache.delete(f"{from_user(message).id}_item_add_message")
    mess = f"{get_user_tag(user)} выставил на продажу {item.quantity} {get_item_emoji(item.name)} за {item.price} {get_item_emoji('бабло')}"
    bot.send_message(message.chat.id, mess)
