# pyright: reportOptionalContextManager=none

from telebot.types import Message, CallbackQuery
from telebot.handler_backends import State, StatesGroup


from config import bot
from helpers.utils import get_item, get_item_emoji, get_middle_item_price, get_user_tag
from database.funcs import database, cache
from database.models import MarketItemModel
from helpers.exceptions import NoResult
from helpers.markups import InlineMarkup


class AddNewItemState(StatesGroup):
    name = State()
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
    with bot.retrieve_data(call.from_user.id, call.message.chat.id) as data:
        data["name"] = item.name

    user = database.users.get(id=call.from_user.id)
    user_item = database.items.get(name=item.name, owner=user._id)

    markup = InlineMarkup.delate_state(user)
    bot.edit_message_text(
        f"<b>Продажа придмета {item.emoji}</b>\nВведи кол-во ({user_item.quantity})",
        call.message.chat.id,
        call.message.id,
        reply_markup=markup,
    )
    bot.set_state(call.from_user.id, AddNewItemState.quantity, call.message.chat.id)

    cache.setex(f"{user.id}_item_add_message", 300, call.message.id)  # type: ignore


@bot.message_handler(
    state=[AddNewItemState.quantity, AddNewItemState.price], is_digit=False
)
def invalid_int_input(message: Message):
    user = database.users.get(id=message.from_user.id)
    markup = InlineMarkup.delate_state(user)
    bot.reply_to(message, "Введите число", reply_markup=markup)


@bot.message_handler(state=AddNewItemState.quantity, is_digit=True)
def quantity_state(message: Message):
    user = database.users.get(id=message.from_user.id)
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        user_item = database.items.get(owner=user._id, name=data["name"])

    if user_item.quantity < int(message.text):  # type: ignore
        bot.reply_to(message, "У тебя нет столько")
        return

    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data["quantity"] = int(message.text)  # type: ignore

    call_message_id = cache.get(f"{message.from_user.id}_item_add_message")
    bot.delete_message(message.chat.id, message.id)

    item = get_item(user_item.name)
    markup = InlineMarkup.delate_state(user)
    bot.edit_message_text(
        f"<b>Продажа придмета {item.emoji}</b>\nВведи прайс (+-{get_middle_item_price(item.name)}/шт)",
        message.chat.id,
        call_message_id,  # type: ignore
        reply_markup=markup,
    )
    bot.set_state(message.from_user.id, AddNewItemState.price, message.chat.id)


@bot.message_handler(state=AddNewItemState.price, is_digit=True)
def price_state(message: Message):
    user = database.users.get(id=message.from_user.id)
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        try:
            user_item = database.items.get(owner=user._id, name=data["name"])
        except NoResult:
            bot.reply_to(message, "У тебя нет такого придмета")
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

    call_message_id = cache.get(f"{message.from_user.id}_item_add_message")

    bot.delete_message(message.chat.id, call_message_id)  # type: ignore
    bot.delete_message(message.chat.id, message.id)

    cache.delete(f"{message.from_user.id}_item_add_message")
    mess = f"{get_user_tag(user)} выставил на продажу {item.quantity} {get_item_emoji(item.name)} за {item.price} {get_item_emoji('бабло')}"
    bot.send_message(message.chat.id, mess)
