import random
from typing import Any, Callable, NoReturn, TypedDict, Union, List
from datetime import timedelta

from telebot.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

from helpers.enums import ItemRarity, ItemType

from .items import items_list


from helpers.exceptions import ItemIsCoin, NoResult
from helpers.utils import (
    Loading,
    award_user_achievement,
    calc_xp_for_level,
    from_user,
    get_achievement,
    get_item,
    get_item_count_for_rarity,
    get_item_emoji,
    get_user_tag,
    utcnow,
)

from database.funcs import BaseDB, database, T as ModelsType
from database.models import (
    DailyGiftModel,
    UserModel,
    ItemModel,
    QuestModel,
    ExchangerModel,
)

from helpers.datatypes import Item

from config import bot


def level_up(user: UserModel, chat_id: Union[str, int, None] = None):
    if user.xp > user.max_xp:
        user.xp = user.xp - user.max_xp
    else:
        user.xp = 0

    user.level += 1
    user.max_xp = calc_xp_for_level(user.level)

    mess = f"{get_user_tag(user)} повисел свой уровень🏵"

    if not chat_id:
        chat_id = user.id

    box = get_or_add_user_item(user, "бокс")

    if box.quantity < 0:
        box.quantity = 0

    box.quantity += 1

    database.items.update(**box.to_dict())
    bot.send_sticker(
        chat_id,
        "CAACAgIAAxkBAAEpjItl0i05sChI02Gz_uGnAtLyPBcJwgACXhIAAuyZKUl879mlR_dkOzQE",  # cSpell:ignore CAAC
    )

    markup = InlineKeyboardMarkup(row_width=1)
    buttons = []
    btn_data = []
    if user.max_items_count_in_market <= 10:
        btn_data.append(("+1 место в ларьке", "market"))
    if user.level >= 10 and user.luck <= 15:
        btn_data.append(("+1 удача", "luck"))

    for data in btn_data:
        buttons.append(
            InlineKeyboardButton(data[0], callback_data=f"levelup {data[1]} {user.id}")
        )

    markup.add(*buttons)
    if len(buttons) != 0:
        mess += "\n\nВыбери что хочешь улучшить"

    bot.send_message(chat_id, mess, reply_markup=markup)


def check_user_stats(user: UserModel, chat_id: Union[str, int, None] = None):
    if not chat_id:
        chat_id = user.id
    if user.xp >= user.max_xp:
        level_up(user, chat_id)

    if user.health < 0:
        user.health = 0
    if user.health > 100:
        user.health = 100

    if user.mood < 0:
        user.mood = 0
    if user.mood > 100:
        user.mood = 100

    if user.fatigue > 100:
        user.fatigue = 100
    if user.fatigue < 0:
        user.fatigue = 0

    if user.hunger < 0:
        user.hunger = 0
    if user.hunger > 100:
        user.hunger = 100

    if user.coin < 0:
        user.coin = 0

    check_achievements(user)

    # TODO edit
    # tg_user = bot.get_chat(user.id)
    # if user.name != tg_user.first_name:
    #     user.name = remove_not_allowed_symbols(tg_user.first_name)

    try:
        dog = database.dogs.get(**{"owner": user._id})
    except NoResult:
        dog = None

    if dog:
        if dog.xp >= dog.max_xp:
            if dog.xp > dog.max_xp:
                dog.xp = dog.xp - dog.max_xp
            else:
                dog.xp = 0
            dog.level += 1
            dog.max_xp = calc_xp_for_level(dog.level)
            bot.send_sticker(
                chat_id,
                "CAACAgIAAxkBAAEpv_Bl24Fgxvez1weA12y4uARuP6JyFgACLQEAAjDUnREQhgS5L57E0TQE",  # cSpell:ignore Fgxvez, ACLQEA
            )
            bot.send_message(chat_id, f"Собачка {dog.name} получил новый уровень")

        if dog.health < 0:
            dog.health = 0
        if dog.health > 100:
            dog.health = 100

        if dog.fatigue > 100:
            dog.fatigue = 100
        if dog.fatigue < 0:
            dog.fatigue = 0

        if dog.hunger < 0:
            dog.hunger = 0
        if dog.hunger > 100:
            dog.hunger = 100

        database.dogs.update(**dog.to_dict())
    database.users.update(**user.to_dict())


def generate_quest(user: UserModel):
    allowed_items = []

    for item in items_list:
        if item.is_task_item:
            allowed_items.append(item)

    item: Item = random.choice(allowed_items)
    quantity = random.randint(2, 10) * user.level
    xp = random.uniform(5.0, 15.0) * user.level
    task_coin = item.task_coin
    reward = random.randint(min(task_coin), max(task_coin)) * quantity  # pyright: ignore

    try:
        old_quest = database.quests.get(**{"owner": user._id})
    except NoResult:
        old_quest = None

    if old_quest:
        database.quests.delete(**old_quest.to_dict())

    quest = QuestModel(
        name=item.name,
        quantity=quantity,
        start_time=utcnow(),
        xp=xp,
        reward=reward,
        owner=user._id,
    )
    database.quests.add(**quest.to_dict())

    return quest


class CraftResource(TypedDict):
    item_name: str
    item_count: int
    user_item_quantity: int


class AvailableCraftItem(TypedDict):
    item_name: str
    resources: list[CraftResource]


def get_available_crafts(user: UserModel) -> list[AvailableCraftItem]:
    available_crafts: list[AvailableCraftItem] = []

    for item in items_list:
        if not item.craft:
            continue

        craft = item.craft
        can_craft = True
        required_resources: List[CraftResource] = []

        for craft_item_name, craft_item_count in craft.items():
            user_item = get_or_add_user_item(user, craft_item_name)
            if (user_item.quantity <= 0) or (user_item.quantity < craft_item_count):
                can_craft = False
                break
            required_resources.append(
                {
                    "item_name": craft_item_name,
                    "item_count": craft_item_count,
                    "user_item_quantity": user_item.quantity,
                }
            )

        if can_craft:
            available_crafts.append(
                {"item_name": item.name, "resources": required_resources}
            )

    available_crafts = sorted(
        available_crafts,
        key=lambda x: max(x["resources"], key=lambda y: y["user_item_quantity"])[
            "user_item_quantity"
        ],
        reverse=True,
    )
    return available_crafts


def generate_exchanger(user: UserModel):
    try:
        old_exchanger = database.exchangers.get(**{"owner": user._id})
        database.exchangers.delete(**old_exchanger.to_dict())
    except NoResult:
        pass

    allowed_items: List[Item] = []
    for item in items_list:
        if item.can_exchange:
            allowed_items.append(item)

    item = random.choice(allowed_items)

    exchange_price = item.exchange_price
    price = random.randint(min(exchange_price), max(exchange_price))  # pyright: ignore

    exchanger = ExchangerModel(
        item=item.name,
        price=price,
        expires=utcnow() + timedelta(days=1),
        owner=user._id,
    )

    exchanger_add = database.exchangers.add(**exchanger.to_dict())
    exchanger._id = exchanger_add.inserted_id
    database.exchangers.update(**exchanger.to_dict())
    return exchanger


def get_available_items_for_use(user: UserModel) -> List[ItemModel]:
    available_items = []
    items = database.items.get_all(**{"owner": user._id})
    for user_item in items:
        item = get_item(user_item.name)
        if item and item.is_consumable and user_item.quantity > 0:
            available_items.append(user_item)

    return sorted(available_items, key=lambda item: item.quantity, reverse=True)


def use_item(message: Message, name: str):
    with Loading(message):
        user = database.users.get(id=from_user(message).id)

        item = get_item(name)

        if not item:
            bot.reply_to(message, "Такого предмета не существует")
            return

        if not item.is_consumable:
            bot.reply_to(message, "Этот предмет нельзя юзать")
            return

        if item.type == ItemType.USABLE:
            bot.reply_to(
                message,
                "Этот предмет нельзя юзать (https://github.com/HamletSargsyan/livebot/issues/41)",
            )
            return

        user_item = get_or_add_user_item(user, item.name)

        if not user_item:
            bot.reply_to(message, f"У тебя нет {item.name} {item.emoji}")
            return

        if user_item.quantity <= 0:
            bot.reply_to(message, f"У тебя нет {item.name} {item.emoji}")
            return

        match item.name:
            case "трава" | "буханка" | "сэндвич" | "пицца" | "тако" | "суп":
                user.hunger -= item.effect  # pyright: ignore
                bot.reply_to(
                    message,
                    f"Поел {item.emoji}\n- {item.effect} голода",
                )
                user_item.quantity -= 1
            case "буст":
                xp = random.randint(100, 150)
                user.xp += xp
                bot.reply_to(
                    message, f"{get_item_emoji(name)} Юзнул буст\n+ {xp} опыта"
                )
                user_item.quantity -= 1
            case "бокс":
                mess = "Ты открыл бокс и получил\n---------\n"
                num_items_to_get = random.randint(1, 3)

                items_to_get = random.choices(
                    items_list,
                    k=num_items_to_get,
                )
                for item_ in items_to_get:
                    quantity = get_item_count_for_rarity(item_.rarity)

                    if quantity == 0:
                        continue
                    mess += f"+ {quantity} {item_.name} {item_.emoji}\n"
                    if item_.name == "бабло":
                        user.coin += quantity
                    else:
                        _item = get_or_add_user_item(user, item_.name)

                        _item.quantity += quantity
                        database.items.update(**_item.to_dict())

                user_item.quantity -= 1

                bot.reply_to(message, mess)
            case "энергос" | "чай":
                user.fatigue -= item.effect  # pyright: ignore
                bot.reply_to(
                    message,
                    f"{item.emoji} юзнул {item.name}\n- {item.effect} усталости",
                )
                user_item.quantity -= 1
            case "пилюля":
                bot.reply_to(message, f"{item.emoji} в разработке")
                return
            case "хелп":
                user.health += item.effect  # pyright: ignore
                bot.reply_to(message, f"{item.effect} юзнул хелп")
                user_item.quantity -= 1
            case "фиксоманчик":
                bot.reply_to(message, f"{item.emoji} в разработке")
                return
            case "водка":
                user.fatigue = 0
                user.health -= item.effect  # pyright: ignore
                bot.reply_to(message, f"{item.emoji} юзнул водку")
                user_item.quantity -= 1
            case "велик":
                if not user.action or user.action.type != "street":
                    bot.reply_to(message, "Ты не гуляешь")
                    return
                minutes = random.randint(10, 45)
                user.action.end -= timedelta(minutes=minutes)
                bot.reply_to(
                    message,
                    f"{item.emoji} юзнул велик и сократил время прогулки на {minutes} минут",
                )
                user_item.quantity -= 1
            case "клевер-удачи":
                user.luck += item.effect  # type: ignore
                user_item.quantity -= 1
                bot.reply_to(message, f"{item.emoji} Увеличил удачу на 1")

        database.users.update(**user.to_dict())
        database.items.update(**user_item.to_dict())
        check_user_stats(user, message.chat.id)


def get_or_add_user_item(user: UserModel, name: str) -> Union[ItemModel, NoReturn]:
    item = get_item(name)

    if item.type != ItemType.COUNTABLE:
        raise ValueError  # TODO: add message
    if item.name == "бабло":
        raise ItemIsCoin

    try:
        item = database.items.get(owner=user._id, name=item.name)
    except NoResult:
        item = ItemModel(owner=user._id, name=item.name)
        id = database.items.add(**item.to_dict()).inserted_id
        item._id = id

    return item


def add_user_usage_item(
    user: UserModel, name: str, usage: float = 0
) -> Union[ItemModel, NoReturn]:
    _item = get_item(name)

    if _item.type != ItemType.USABLE:
        raise ValueError  # TODO: add message

    item = ItemModel(owner=user._id, name=_item.name, usage=usage)
    id = database.items.add(**item.to_dict()).inserted_id
    item._id = id

    return item


def get_or_add_user_usable_items(
    user: UserModel, name: str, usage: float = 0
) -> Union[list[ItemModel], NoReturn]:
    item = get_item(name)

    if item.type != ItemType.USABLE:
        raise ValueError  # TODO: add message

    try:
        items = database.items.get_all(owner=user._id, name=item.name)
        if len(items) == 0:
            raise NoResult
    except NoResult:
        items = [add_user_usage_item(user, name, usage)]

    return items


def transfer_usable_item(from_user_item: ItemModel, to_user: UserModel):
    from_user_item.owner = to_user._id
    database.items.update(**from_user_item.to_dict())


def transfer_countable_item(
    from_user_item: ItemModel, quantity: int, to_user: UserModel
):
    to_user_item = get_or_add_user_item(to_user, from_user_item.name)

    if from_user_item.quantity < quantity:
        raise  # TODO

    from_user_item.quantity -= quantity
    to_user_item.quantity += quantity

    database.items.update(**from_user_item.to_dict())
    database.items.update(**to_user_item.to_dict())


def get_top(
    name: str,
    collection: BaseDB[ModelsType],
    filter_: Callable[[ModelsType], bool],
    sort_key: Callable[[ModelsType], Any],
    key: Callable[[ModelsType], str],
    value: Callable[[ModelsType], int],
    max_index: int = 20,
) -> str:
    objects = collection.get_all()
    objects.sort(key=sort_key, reverse=True)
    mess = f"<b>Топ {max_index} - {name}</b>\n\n"
    objects = filter(filter_, objects)

    for index, obj in enumerate(objects, start=1):
        mess += f"{index}. {key(obj)[:20]} - {value(obj)}\n"
        if index == max_index:
            break
    return mess


def coin_top(max_index: int = 20):
    return get_top(
        "бабло",
        database.users,
        lambda o: o.coin > 0,
        lambda o: o.coin,
        lambda o: o.name,
        lambda o: o.coin,
        max_index,
    )


def level_top(max_index: int = 20):
    return get_top(
        "уровень",
        database.users,
        lambda o: o.level > 0,
        lambda o: o.level,
        lambda o: o.name,
        lambda o: o.level,
        max_index,
    )


def dog_level_top(max_index: int = 20):
    return get_top(
        "уровень собак",
        database.dogs,
        lambda o: o.level > 0,
        lambda o: o.level,
        lambda o: o.name,
        lambda o: o.level,
        max_index,
    )


def generate_daily_gift(user: UserModel):
    try:
        daily_gift = database.daily_gifts.get(owner=user._id)
    except NoResult:
        daily_gift = DailyGiftModel(owner=user._id)
        id = database.daily_gifts.add(**daily_gift.to_dict()).inserted_id
        daily_gift._id = id

    items = list(filter(lambda i: i.rarity == ItemRarity.COMMON, items_list))
    items = random.choices(items, k=random.randint(1, 3))
    daily_gift.items = [item.name for item in items]
    daily_gift.is_claimed = False
    daily_gift.next_claimable_at = utcnow() + timedelta(days=1)
    database.daily_gifts.update(**daily_gift.to_dict())
    return daily_gift


def check_achievements(user: UserModel):
    for key in list(user.achievement_progress):
        ach = get_achievement(key.replace("-", " "))
        if ach.check(user):
            award_user_achievement(user, ach)
