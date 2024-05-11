from telebot.types import Message, CallbackQuery
from telebot.handler_backends import State, StatesGroup


from config import bot
from helpers.utils import get_item, get_item_emoji, get_user_tag
from database.funcs import database, cache
from database.models import MarketItemModel


class AddNewItemState(StatesGroup):
    name = State()
    quantity = State()
    price = State()


@bot.callback_query_handler(state=AddNewItemState.name, func=lambda c: c.data.startswith("sell"))
def name_state(call: CallbackQuery):
    data = call.data.split(" ")

    if data[-1] != str(call.from_user.id):
        return
    
    
    item = get_item(data[1])
    with bot.retrieve_data(call.from_user.id, call.message.chat.id) as data:
        data["name"] = item.name
    
    user = database.users.get(id=call.from_user.id)
    user_item = database.items.get(name=item.name, owner=user._id)
    
    bot.edit_message_text(f"<b>Продажа придмета {item.emoji}</b>\nВведи кол-во ({user_item.quantity})", call.message.chat.id, call.message.id)
    bot.set_state(call.from_user.id, AddNewItemState.quantity, call.message.chat.id)
    
    cache.setex(f"{user.id}_item_add_message", 300, call.message.id)



@bot.message_handler(state=[AddNewItemState.quantity, AddNewItemState.price], is_digit=False)
def invalid_int_input(message: Message):
    bot.reply_to(message, "Введите число")


@bot.message_handler(state=AddNewItemState.quantity, is_digit=True)
def quantity_state(message: Message):
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data["quantity"] = int(message.text)
    
    call_message_id = cache.get(f"{message.from_user.id}_item_add_message")
    bot.edit_message_text("Введи прайс", message.chat.id, call_message_id)
    bot.set_state(message.from_user.id, AddNewItemState.price, message.chat.id)



@bot.message_handler(state=AddNewItemState.price, is_digit=True)
def price_state(message: Message):
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        user = database.users.get(id=message.from_user.id)
        item = MarketItemModel(
            name=data['name'].lower(),
            quantity=int(data['quantity']),
            price=int(message.text),
            owner=user._id
        )


    call_message_id = cache.get(f"{message.from_user.id}_item_add_message")
    bot.delete_state(user.id, call_message_id)
    database.market_items.add(**item.to_dict())

    mess = f"{get_user_tag(user)} выстовил на продажу {item.quantity} {get_item_emoji(item.name)} за {item.price}/шт {get_item_emoji('бабло')}"
    bot.send_message(message.chat.id, mess)

