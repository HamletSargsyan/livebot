from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from helpers.consts import COIN_EMOJI
from helpers.enums import ItemType
from helpers.filters import IsDigitFilter
from helpers.utils import (
    get_item,
    get_item_emoji,
    get_middle_item_price,
    get_user_tag,
)
from database.funcs import database, redis_cache
from database.models import MarketItemModel
from helpers.exceptions import NoResult
from helpers.markups import InlineMarkup


router = Router()


class AddNewItemState(StatesGroup):
    name = State()
    item_oid = State()
    quantity = State()
    price = State()


@router.callback_query(StateFilter(AddNewItemState.name), F.data.startswith("sell"))
async def name_state(call: CallbackQuery, state: FSMContext):
    data = call.data.split(" ")

    if data[-1] != str(call.from_user.id):
        return

    item = get_item(data[1])

    if item.type == ItemType.USABLE:
        await call.message.edit_text(
            "Этот предмет нельзя продавать (https://github.com/HamletSargsyan/livebot/issues/41)",
        )
        return

    await state.update_data(name=item.name)

    user = await database.users.async_get(id=call.from_user.id)
    user_item = await database.items.async_get(name=item.name, owner=user._id)

    markup = InlineMarkup.delate_state(user)
    await call.message.edit_text(
        f"<b>Продажа предмета {item.emoji}</b>\nВведи кол-во ({user_item.quantity})",
        reply_markup=markup,
    )
    await state.set_state(AddNewItemState.quantity)

    redis_cache.setex(f"{user.id}_item_add_message", 300, call.message.message_id)  # type: ignore


# TODO
@router.message(StateFilter(AddNewItemState.item_oid), IsDigitFilter())
def select_item_state(message: Message, state: FSMContext): ...


@router.message(StateFilter(AddNewItemState.quantity, AddNewItemState.price), ~IsDigitFilter())
async def invalid_int_input(message: Message):
    user = await database.users.async_get(id=message.from_user.id)
    markup = InlineMarkup.delate_state(user)
    await message.reply("Введите число", reply_markup=markup)


@router.message(StateFilter(AddNewItemState.quantity), IsDigitFilter())
async def quantity_state(message: Message, state: FSMContext):
    user = await database.users.async_get(id=message.from_user.id)
    data = await state.get_data()
    user_item = await database.items.async_get(owner=user._id, name=data.get("name"))
    await state.update_data(user_item=user_item)

    if user_item.quantity < int(message.text):  # type: ignore
        await message.reply("У тебя нет столько")
        return

    await state.update_data(quantity=int(message.text))  # type: ignore

    call_message_id = redis_cache.get(f"{message.from_user.id}_item_add_message")

    await message.delete()

    item = get_item(user_item.name)
    markup = InlineMarkup.delate_state(user)
    await message.bot.edit_message_text(
        f"<b>Продажа предмета {item.emoji}</b>\nВведи прайс (+-{get_middle_item_price(item.name)}/шт)",
        message_id=call_message_id,  # type: ignore
        chat_id=message.chat.id,
        reply_markup=markup,
    )

    await state.set_state(AddNewItemState.price)


@router.message(StateFilter(AddNewItemState.price), IsDigitFilter())
async def price_state(message: Message, state: FSMContext):
    user = await database.users.async_get(id=message.from_user.id)

    data = await state.get_data()
    try:
        user_item = await database.items.async_get(owner=user._id, name=data.get("name"))
    except NoResult:
        await message.reply("У тебя нет такого предмета")
        return

    if user_item.quantity < data.get("quantity"):  # type: ignore
        await message.reply("У тебя нет столько")
        return

    item = MarketItemModel(
        name=data.get("name").lower(),
        quantity=data.get("quantity"),  # type: ignore
        price=int(message.text),  # type: ignore
        owner=user._id,
    )

    await state.clear()
    database.market_items.add(**item.to_dict())
    user_item.quantity -= item.quantity
    await database.items.async_update(**user_item.to_dict())

    call_message_id = redis_cache.get(f"{message.from_user.id}_item_add_message")

    await message.bot.delete_message(message.chat.id, call_message_id)  # type: ignore
    await message.delete()

    redis_cache.delete(f"{message.from_user.id}_item_add_message")
    mess = f"{get_user_tag(user)} выставил на продажу {item.quantity} {get_item_emoji(item.name)} за {item.price} {COIN_EMOJI}"
    await message.bot.send_message(message.chat.id, mess)
