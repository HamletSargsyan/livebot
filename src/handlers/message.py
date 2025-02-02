import random

from aiogram import Router
from aiogram.enums import ChatType
from aiogram.filters import (
    IS_MEMBER,
    IS_NOT_MEMBER,
    ChatMemberUpdatedFilter,
    Command,
    CommandObject,
    CommandStart,
)
from aiogram.types import (
    ChatMemberUpdated,
    KeyboardButton,
    Message,
)
from aiogram.utils.keyboard import ReplyKeyboardBuilder

import base.user_input  # noqa  # pylint: disable=unused-import
from base.items import ITEMS
from base.player import (
    check_user_stats,
    coin_top,
    generate_daily_gift,
    generate_exchanger,
    generate_quest,
    get_available_crafts,
    get_available_items_for_use,
    get_or_add_user_item,
    transfer_countable_item,
)
from base.weather import get_weather
from config import VERSION, config
from database.funcs import database
from helpers.consts import COIN_EMOJI
from helpers.enums import ItemType
from helpers.exceptions import ItemNotFoundError, NoResult
from helpers.filters import ChatTypeFilter
from helpers.markups import InlineMarkup
from helpers.utils import (
    Loading,
    batched,
    check_user_subscription,
    check_version,
    get_item,
    get_item_emoji,
    get_middle_item_price,
    get_time_difference_string,
    get_user_tag,
    increment_achievement_progress,
    quick_markup,
    safe,
    send_channel_subscribe_message,
    utcnow,
)

router = Router()

start_markup_builder = ReplyKeyboardBuilder()
if config.event.open:
    start_markup_builder.add(KeyboardButton(text="Ивент"))

start_markup_builder.add(
    KeyboardButton(text="Профиль"),
    KeyboardButton(text="Дом"),
    KeyboardButton(text="Инвентарь"),
    KeyboardButton(text="Квест"),
    KeyboardButton(text="Магазин"),
    KeyboardButton(text="Рынок"),
    KeyboardButton(text="Верстак"),
    KeyboardButton(text="Топ"),
    KeyboardButton(text="Юз"),
    KeyboardButton(text="Статы"),
    KeyboardButton(text="Погода"),
    KeyboardButton(text="Обменник"),
    KeyboardButton(text="Гайд"),
    KeyboardButton(text="Достижения"),
)

start_markup_builder.adjust(3)
START_MARKUP = start_markup_builder.as_markup()  # pylint: disable=assignment-from-no-return


@router.message(CommandStart())
async def start(message: Message, command: CommandObject):
    async with Loading(message):
        user_id = message.from_user.id

        user = await database.users.async_get(id=message.from_user.id)

        mess = f"Здорова {user.name}, добро пожаловать в игру\n\nПомощь: /help"

        if param := command.args:
            users_id = [str(user.id) for user in await database.users.async_get_all()]

            if param in users_id:
                if str(user_id) == param:
                    await message.reply(mess)
                    return
                if user is not None:
                    await message.reply(mess)
                    return
                ref_user = user = await database.users.async_get(id=int(param))
                if not ref_user:
                    await message.reply(mess, reply_markup=START_MARKUP)
                    return
                user = await database.users.async_get(id=message.from_user.id)

                coin = random.randint(5000, 15000)
                ref_user.coin += coin
                await database.users.async_update(**ref_user.to_dict())
                increment_achievement_progress(ref_user, "друзья навеки")

                await safe(
                    message.bot.send_message(
                        ref_user.id,
                        (
                            f"{user.name} присоединился к игре благодаря твой реферальной ссылке\n"
                            f"Ты получил {coin} бабла {get_item_emoji('бабло')}"
                        ),
                    )
                )

                return

        if message.chat.type != "private":
            markup = None
        else:
            markup = START_MARKUP

        await message.reply(mess, reply_markup=markup)


@router.message(Command("help"))
async def help(message: Message):
    mess = (
        "<b>Помощь</b>\n\n"
        "<b>Канал:</b> @LiveBotOfficial\n"
        "<b>Чат</b>: @LiveBotOfficialChat\n"
        "<b>Гайд</b>: https://hamletsargsyan.github.io/livebot/guide\n"
    )

    await message.reply(mess)


@router.message(Command("profile"))
async def profile_cmd(message: Message):
    async with Loading(message):
        if message.reply_to_message:
            user = user = await database.users.async_get(id=message.reply_to_message.id)
        else:
            user = await database.users.async_get(id=message.from_user.id)

        await check_user_stats(user, message.chat.id)

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
        await message.reply(mess)


@router.message(Command("bag"))
async def bag_cmd(message: Message):
    async with Loading(message):
        user = await database.users.async_get(id=message.from_user.id)

        mess = "<b>Рюкзак</b>\n\n"
        inventory = await database.items.async_get_all(owner=user._id)
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

        await message.reply(mess)


@router.message(Command("items"))
async def items_cmd(message: Message):
    async with Loading(message):
        mess = f"<b>Предметы</b>\n\n1 / {len(list(batched(ITEMS, 6)))}"
        user = await database.users.async_get(id=message.from_user.id)
        markup = markup = InlineMarkup.items_pager(user=user)

        await message.reply(mess, reply_markup=markup)


@router.message(Command("shop"))
async def shop_cmd(message: Message):
    async with Loading(message):
        args = message.text.split(" ")

        if len(args) != 3:
            items = list(filter(lambda item: item.price, ITEMS))
            items.sort(key=lambda item: item.price, reverse=True)  # type: ignore
            mess = "<b>🛍Магазин🛍</b>\n\n"
            for item in items:
                if not item.price:
                    continue

                mess += f"{item.emoji} {item.name} - {item.price}/шт.\n"
            await message.reply(mess)
            return

        err_mess = "Что-то не так написал\nНадо: <code>/shop [имя предмета] [кол-во]</code>"

        if len(args) != 3:
            await message.reply(err_mess)
            return

        user = await database.users.async_get(id=message.from_user.id)

        item_name = args[1]
        try:
            count = int(args[2])
        except (ValueError, IndexError):
            count = 1

        if not get_item(item_name):
            await message.reply("Такого предмета не существует")
            return

        item = get_item(item_name)

        if not item.price:
            await message.reply("Этот предмет нельзя купить, у него нет цены")
            return

        price = item.price * count
        if user.coin < price:
            await message.reply("У тебя нет столько бабла, иди работать")
            return

        user.coin -= price
        user_item = get_or_add_user_item(user, get_item(item.name).name)

        user_item.quantity += count
        await database.users.async_update(**user.to_dict())
        await database.items.async_update(**user_item.to_dict())

        emoji = get_item_emoji(item.name)
        await message.reply(
            f"Купил {count} {item.name} {emoji} за {price} {COIN_EMOJI}",
        )


@router.message(Command("casino"))
async def casino(message: Message, command: CommandObject):
    async with Loading(message):
        count = command.args

        if not count:
            mess = (
                "<b>🎰Казино🎰</b>\n\n"
                "Решил заработать легкие деньги? Ну давай\n"
                "Шансы 50 на 50\n"
                "Чтобы сыграть напиши <code>/casino [кол-во]</code>"
            )
            await message.reply(mess)
            return

        try:
            count = int(count)
        except ValueError:
            count = 1

        user = await database.users.async_get(id=message.from_user.id)

        ticket = get_or_add_user_item(user, "билет")

        if (not ticket) or (ticket.quantity <= 0):
            await message.reply(
                f"Чтобы сыграть в казино у тебя должен быть билет {get_item_emoji('билет')}",
            )
            return

        chance = random.randint(0, 10)

        if count > user.coin:
            await message.reply(
                f"Нифига се цифры, у тебя есть только {user.coin} {get_item_emoji('бабло')}",
            )
            return

        if count <= 0:
            count = 1

        if user.coin <= 0:
            await message.reply("Кудаа, у тебя нет бабла, иди работать")
            return

        await message.answer_dice("🎲")
        ticket.quantity -= 1
        if chance <= 5:
            await message.answer(f"Блин, сорян\n——————\n-{count}")
            user.coin -= count
            user.casino_loose += count

        else:
            await message.answer(f"Нифига се\n——————\n+{count * 2}")
            user.coin += count * 2
            user.casino_win += count * 2

        await database.users.async_update(**user.to_dict())
        await database.items.async_update(**ticket.to_dict())
        await check_user_stats(user, message.chat.id)


@router.message(Command("workbench"))
@router.message(Command("craft"))
async def workbench_cmd(message: Message):
    async with Loading(message):
        user = await database.users.async_get(id=message.from_user.id)

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

                    print(get_item_emoji(item_name), item_name, get_item(item_name).emoji)
                    craft_str = f"{get_item_emoji(item_name)} {item_name} - {possible_crafts}\n"
                    mess += f"{craft_str}"
            print(mess)
            await message.reply(mess)
            return

        name = args[1].lower()
        try:
            count = int(args[2])
        except (ValueError, IndexError):
            count = 1

        if not get_item(name):
            await message.reply("Такого предмета не существует")
            return

        item_data = get_item(name)

        if not item_data.craft:
            await message.reply(f"У {item_data.emoji} нет крафта")
            return

        craft = item_data.craft

        for craft_item in craft.items():
            user_item = get_or_add_user_item(user, craft_item[0])
            if (
                (not user_item)
                or (user_item.quantity <= 0)
                or (user_item.quantity < craft_item[1] * count)
            ):
                await message.reply("Недостаточно предметов")
                return

            user_item.quantity -= craft_item[1] * count
            await database.items.async_update(**user_item.to_dict())

        item = get_or_add_user_item(user, name)

        item.quantity += count
        xp = random.uniform(5.0, 10.0) * count
        if random.randint(1, 100) < user.luck:
            xp += random.uniform(2.3, 6.7)

        user.xp += xp

        await database.items.async_update(**item.to_dict())
        await database.users.async_update(**user.to_dict())
        await message.reply(f"Скрафтил {count} {name} {get_item_emoji(name)}\n+ {int(xp)} хп")

        await check_user_stats(user, message.chat.id)


@router.message(Command("transfer"))
async def transfer_cmd(message: Message):
    async with Loading(message):
        if not message.reply_to_message:
            await message.reply("Кому кидать собрался??")
            return

        user = await database.users.async_get(id=message.from_user.id)
        reply_user = await database.users.async_get(id=message.reply_to_message.id)

        args = message.text.split(" ")

        err_mess = (
            "Что-то не так написал, надо так:\n<code>/transfer [имя предмета] [кол-во]</code>"
        )

        if len(args) < 2:
            await message.reply(err_mess)
            return

        item_name = args[1].lower()
        try:
            item = get_item(item_name)
        except ItemNotFoundError:
            await message.reply(f"{item_name}??\nСерьёзно?\n\nТакого предмета не существует")
            return

        try:
            quantity = int(args[2])
        except (ValueError, IndexError):
            quantity = 1

        if item_name == "бабло":
            if user.coin <= 0:
                await message.reply(f"У тебя нет <i>{item_name}</i>")
                return
            if user.coin <= quantity:
                await message.reply("У тебя Недостаточно бабла, иди работать")
                return
            user.coin -= quantity
            reply_user.coin += quantity
        else:
            if item.type == ItemType.USABLE:
                mess = "Выбери какой"
                markup = InlineMarkup.transfer_usable_items(user, reply_user, item_name)

                await message.reply(mess, reply_markup=markup)
                return

            user_item = get_or_add_user_item(user, item_name)

            if (user_item.quantity < quantity) or (user_item.quantity <= 0):
                await message.reply(f"У тебя нет <i>{item_name}</i>")
                return
            transfer_countable_item(user_item, quantity, reply_user)

        mess = (
            f"{user.name} подарил {reply_user.name}\n"
            "----------------\n"
            f"{item.emoji} {item_name} {quantity}"
        )

        await database.users.async_update(**user.to_dict())
        await database.users.async_update(**reply_user.to_dict())

        await message.answer(mess)


@router.message(Command("event"))
async def event_cmd(message: Message):
    async with Loading(message):
        user = await database.users.async_get(id=message.from_user.id)
        markup = quick_markup(
            {"Гайд": {"url": "https://hamletsargsyan.github.io/livebot/guide/#ивент"}}
        )

        if config.event.open is False:
            if config.event.start_time < utcnow():
                await message.reply("Ивент закончился", reply_markup=markup)
            else:
                time_difference = get_time_difference_string(config.event.start_time - utcnow())
                await message.reply(
                    f"До начала ивента осталось {time_difference}",
                    reply_markup=markup,
                )
            return

        time_difference = config.event.end_time - utcnow()
        time_left = get_time_difference_string(time_difference)

        mess = (
            "<b>Ивент 🎃</b>\n\n"
            "Собирай 🍬 и побеждай\n\n"
            "Конфеты можно получать во время прогулки и в боксе\n\n"
            f"<b>До окончания осталось:</b> {time_left}\n\n"
            "<b>Топ 10 по 🍬</b>\n\n"
        )

        items = await database.items.async_get_all(name="конфета")
        sorted_items = sorted(items, key=lambda item: item.quantity, reverse=True)
        for index, item in enumerate(sorted_items, start=1):
            if item.quantity > 0:
                owner = await database.users.async_get(**{"_id": item.owner})
                mess += f"{index}. {owner.name} - {item.quantity}\n"
            if index == 10:
                break

        item = get_or_add_user_item(user, "конфета")
        mess += f"\n\nТы собрал: {item.quantity}"
        await message.reply(mess, reply_markup=markup)


@router.message(Command("top"))
async def top_cmd(message: Message):
    async with Loading(message):
        mess = coin_top()

        markup = quick_markup(
            {
                "🪙": {"callback_data": f"top coin {message.from_user.id}"},
                "🏵": {"callback_data": f"top level {message.from_user.id}"},
                "🐶": {"callback_data": f"top dog_level {message.from_user.id}"},
            }
        )

        await message.reply(mess, reply_markup=markup)


@router.message(Command("use"))
async def use_cmd(message: Message):
    async with Loading(message):
        user = await database.users.async_get(id=message.from_user.id)

        args = message.text.split(" ")

        if len(args) < 2:
            items = get_available_items_for_use(user)
            markup = InlineMarkup.use(user, items)

            if items:
                mess = "<b>Доступные предметы для юза</b>\n\n"
            else:
                mess = "Нет доступных предметов для юза"
            await message.reply(mess, reply_markup=markup)
            return


@router.message(Command("ref"))
async def ref_cmd(message: Message):
    async with Loading(message):
        user = await database.users.async_get(id=message.from_user.id)

        mess = (
            "Хочешь заработать?\n"
            "Ты по адресу, пригласи друзей и получи от 5к до 15к бабла\n"
            f"Вот твоя ссылочка: https://t.me/{(await message.bot.me()).username}?start={user.id}"
        )
        await message.reply(mess)


@router.message(Command("promo"))
async def promo(message: Message) -> None:
    async with Loading(message):
        user = await database.users.async_get(id=message.from_user.id)

        await message.delete()
        if not await check_user_subscription(user):
            await send_channel_subscribe_message(message)
            return

        text = message.text.split(" ")

        if len(text) != 1:
            text = text[1]

            code = await database.promos.async_get(name=text)
            if code:
                promo_users = code.users
                if user.id in promo_users:
                    await message.answer("Ты уже активировал этот промокод")
                    return

                if code.is_used:
                    await message.answer("Этот промокод уже активировали")
                    return

                code.usage_count -= 1

                if code.usage_count <= 0:
                    code.usage_count = 0
                    code.is_used = True

                mess = f"Ухтыы, {user.name} активировал промо и получил\n\n"
                for item in code.items:
                    if item == "бабло":
                        user.coin += code.items[item]
                        await database.users.async_update(**user.to_dict())
                    else:
                        user_item = get_or_add_user_item(user, item)
                        user_item.quantity += code.items[item]
                        await database.items.async_update(**user_item.to_dict())
                    mess += f"+ {code.items[item]} {item} {get_item_emoji(item)}\n"
                promo_users.append(user.id)
                code.users = promo_users

                await database.promos.async_update(**code.to_dict())
                await message.answer_sticker(
                    "CAACAgIAAxkBAAEpjI9l0i13xK0052Ruta0D5a5lWozGBgACHQMAAladvQrFMjBk7XkPEzQE",
                )
                await message.answer(mess)
            else:
                await message.answer("Такого промокода не существует")


@router.message(Command("stats"))
async def stats_cmd(message: Message):
    async with Loading(message):
        user = await database.users.async_get(id=message.from_user.id)

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

        await message.reply(mess)


@router.message(Command("quest"))
async def quest_cmd(message: Message):
    async with Loading(message):
        user = await database.users.async_get(id=message.from_user.id)
        try:
            quest = await database.quests.async_get(owner=user._id)
        except NoResult:
            quest = None

        if not quest:
            quest = generate_quest(user)
        if not user.new_quest_coin_quantity:
            user.new_quest_coin_quantity = 2

        item = get_or_add_user_item(user, quest.name)

        finish_button_text = (
            f"{item.quantity} / {quest.quantity}" if item.quantity < quest.quantity else "Завершить"
        )

        markup = quick_markup(
            {
                finish_button_text: {"callback_data": f"finish_quest {user.id}"},
                "Пропуск": {"callback_data": f"skip_quest {user.id}"},
            }
        )

        mess = (
            "<b>Квест</b>\n\n"
            f"<i>Собери {quest.quantity} {quest.name} {get_item_emoji(quest.name)}</i>\n\n"
            f"<b>Награда:</b> {quest.reward} {get_item_emoji('бабло')}"
        )

        await message.reply(mess, reply_markup=markup)


@router.message(Command("weather"))
async def weather_cmd(message: Message):
    async with Loading(message):
        weather = get_weather()

        mess = (
            f"<b>{weather.current.emoji} Прогноз погоды</b>\n\n"
            f"{weather.current.temperature_2m} {weather.current_units.temperature_2m}\n"
            f"{weather.current.ru_type}"
        )

        await message.reply(mess)


@router.message(Command("exchanger"))
async def exchanger_cmd(message: Message):
    # if True:
    #     await message.reply(
    #         (
    #             "Временно не работает из-за"
    #             "<a href='https://github.com/HamletSargsyan/livebot/issues/18'>бага</a> :("
    #         ),
    #     )
    #     return
    async with Loading(message):
        user = await database.users.async_get(id=message.from_user.id)
        markup = quick_markup(
            {"Гайд": {"url": "https://hamletsargsyan.github.io/livebot/guide/#обменник"}}
        )

        if user.level < 5:
            await message.reply("Обменник доступен с 5 уровня", reply_markup=markup)
            return

        try:
            exchanger = await database.exchangers.async_get(owner=user._id)
        except NoResult:
            exchanger = generate_exchanger(user)

        if exchanger.expires < utcnow():
            exchanger = generate_exchanger(user)
            await database.exchangers.async_update(**exchanger.to_dict())

        time_difference = get_time_difference_string(exchanger.expires - utcnow())
        mess = (
            "<b>Обменник 🔄</b>\n\n"
            f"<b>Предмет:</b> {exchanger.item} {get_item_emoji(exchanger.item)}\n"
            f"<b>Цена за 1 шт:</b> {exchanger.price} {COIN_EMOJI}\n"
            f"<b>Новый предмет появится через:</b> {time_difference}\n"
        )

        args = message.text.split(" ")

        if len(args) < 2:
            await message.reply(mess, reply_markup=markup)
            return

        try:
            quantity = int(args[1])
        except (ValueError, IndexError):
            quantity = 1

        user_item = get_or_add_user_item(user, exchanger.item)

        if not user_item:
            await message.reply(
                f"У тебя нет {get_item_emoji(exchanger.item)}",
                reply_markup=markup,
            )
            return

        if user_item.quantity < quantity:
            await message.reply("Тебе не хватает", reply_markup=markup)
            return

        coin = quantity * exchanger.price
        user.coin += coin
        user_item.quantity -= quantity

        await database.users.async_update(**user.to_dict())
        await database.items.async_update(**user_item.to_dict())

        emoji = get_item_emoji(exchanger.item)
        await message.reply(
            f"Обменял {quantity} {emoji} за {coin} {COIN_EMOJI}",
            reply_markup=markup,
        )


@router.message(Command("dog"))
async def dog_cmd(message: Message):
    async with Loading(message):
        user = await database.users.async_get(id=message.from_user.id)

        try:
            dog = await database.dogs.async_get(owner=user._id)
        except NoResult:
            dog = None

        if not dog:
            await message.reply("У тебя нет собачки")
            return

        # pylint: disable=duplicate-code
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

        await message.reply(mess, reply_markup=markup)


@router.message(Command("rename_dog"))
async def rename_dog_command(message: Message):
    async with Loading(message):
        user = await database.users.async_get(id=message.from_user.id)

        try:
            dog = await database.dogs.async_get(owner=user._id)
        except NoResult:
            dog = None

        if not dog:
            await message.reply("У тебя нет собачки")
            return

        try:
            name = message.text.split(" ")[1]
        except KeyError:
            await message.reply("По моему ты забыл написать имя")
            return

        dog.name = name
        await database.dogs.async_update(**dog.to_dict())

        await message.reply("Переименовал собачку")


@router.message(Command("price"))
async def price_cmd(message: Message):
    async with Loading(message):
        try:
            name = message.text.split(" ")[1].lower()
        except KeyError:
            await message.reply("По моему ты что-то забыл...")
            return

        try:
            item = get_item(name)
        except ItemNotFoundError:
            await message.reply("такого предмета не существует")
            return
        price = get_middle_item_price(item.name)
        if not item:
            mess = "Такого предмета не существует"
        elif price:
            mess = f"Прайс {item.name} {item.emoji} ⸻ {price} {get_item_emoji('бабло')}"
        else:
            mess = f"У {item.emoji} пока нет прайса"

        await message.reply(mess)


@router.message(Command("home"))
async def home_cmd(message: Message):
    async with Loading(message):
        user = await database.users.async_get(id=message.from_user.id)
        mess = "🏠 Дом милый дом"

        markup = InlineMarkup.home_main(user)

        await message.reply(mess, reply_markup=markup)


@router.message(Command("guide"))
async def guide_cmd(message: Message):
    mess = "Гайд по LiveBot 🍃"
    markup = quick_markup({"Читать": {"url": "https://hamletsargsyan.github.io/livebot/guide"}})

    await message.answer(mess, reply_markup=markup)


@router.message(Command("market"))
async def market_cmd(message: Message):
    user = await database.users.async_get(id=message.from_user.id)

    mess = "<b>Рынок</b>\n\n"

    market_items = database.market_items.get_all()
    markup = InlineMarkup.market_pager(user)
    mess += f"1 / {len(list(batched(market_items, 6)))}"

    await message.reply(mess, reply_markup=markup)


@router.message(Command("daily_gift"))
async def daily_gift_cmd(message: Message):
    user = await database.users.async_get(id=message.from_user.id)

    if not await check_user_subscription(user):
        await send_channel_subscribe_message(message)
        return

    try:
        daily_gift = database.daily_gifts.get(owner=user._id)
    except NoResult:
        daily_gift = generate_daily_gift(user)

    mess = "<b>Ежедневный подарок</b>"

    if daily_gift.next_claimable_at <= utcnow():
        daily_gift = generate_daily_gift(user)

    markup = InlineMarkup.daily_gift(user, daily_gift)
    await message.reply(mess, reply_markup=markup)


@router.message(Command("version"))
async def version_cmd(message: Message):
    mess = f"<b>Версия бота</b>: <code>{VERSION}</code> | <i>{check_version()}</i>\n"
    markup = quick_markup(
        {"Релиз": {"url": f"https://github.com/HamletSargsyan/livebot/releases/tag/v{VERSION}"}}
    )
    await message.reply(mess, reply_markup=markup)


@router.message(Command("time"))
async def time_cmd(message: Message):
    time = utcnow().strftime("%H:%M:%S %d.%m.%Y")
    mess = f"Сейчас <code>{time}</code> по UTC"
    await message.reply(mess)


@router.message(Command("achievements"))
async def achievements_cmd(message: Message):
    user = await database.users.async_get(id=message.from_user.id)

    markup = InlineMarkup.achievements(user)

    mess = "Достижения"
    await message.reply(mess, reply_markup=markup)


@router.message(Command("rules"))
async def rules_cmd(message: Message):
    mess = "Правила"

    markup = quick_markup({"Читать": {"url": "https://hamletsargsyan.github.io/livebot/rules"}})

    await message.reply(mess, reply_markup=markup)


@router.message(Command("violations"))
async def violations_cmd(message: Message):
    user = await database.users.async_get(id=message.from_user.id)

    if len(user.violations) == 0:
        await message.reply("У тебя нет нарушений")
        return

    mess = "<b>Нарушения</b>\n\n"

    for i, violation in enumerate(user.violations, start=1):
        until = (
            f" | осталось {get_time_difference_string(violation.until_date - utcnow())}"
            if violation.until_date
            else ""
        )
        mess += f"{i}. {violation.type}{until}\n"
        mess += f"    <i>{violation.reason}</i>\n\n"

    await message.reply(mess)


@router.message(Command("event_shop"))
async def event_shop_cmd(message: Message):
    user = await database.users.async_get(id=message.from_user.id)
    user_event_item = get_or_add_user_item(user, "конфета")

    item = get_item(user_event_item.name)

    mess = "<b>Ивентовый магазин</b>\n\n"
    mess += f"У тебя {user_event_item.quantity} {item.emoji}"

    markup = InlineMarkup.event_shop(user)

    await message.reply(mess, reply_markup=markup)


# ---------------------------------------------------------------------------- #


@router.chat_member(
    ChatMemberUpdatedFilter(IS_NOT_MEMBER >> IS_MEMBER),
    ChatTypeFilter(ChatType.GROUP, ChatType.SUPERGROUP),
)
async def new_chat_member(event: ChatMemberUpdated):
    markup = quick_markup(
        {
            "Правила": {
                "url": "https://hamletsargsyan.github.io/livebot/rules",
            },
        }
    )
    user = await database.users.async_get(id=event.from_user.id)
    if str(event.chat.id) == config.telegram.chat_id:
        mess = (
            f"👋 Привет {get_user_tag(user)}, добро пожаловать в официальный чат по лайвботу 💙\n\n"
        )
    else:
        mess = f"👋 {get_user_tag(user)} присоединился к чату"
    await event.answer(mess, reply_markup=markup)


@router.chat_member(
    ChatMemberUpdatedFilter(IS_MEMBER >> IS_NOT_MEMBER),
    ChatTypeFilter(ChatType.GROUP, ChatType.SUPERGROUP),
)
async def left_chat_member(event: ChatMemberUpdated):
    user = await database.users.async_get(id=event.from_user.id)
    mess = f"😢 {get_user_tag(user)} покинул чат"
    await event.answer(mess)


@router.message()
async def text_message_handler(message: Message):
    user = await database.users.async_get(id=message.from_user.id)
    text = message.text.lower().strip()

    match text:
        case "профиль":
            await profile_cmd(message)
        case "инвентарь" | "портфель" | "инв":
            await bag_cmd(message)
        case _ if text.startswith(("магазин", "шоп")):
            await shop_cmd(message)
        case _ if text.startswith(("крафт", "верстак")):
            await workbench_cmd(message)
        case "топ" | "рейтинг":
            await top_cmd(message)
        case "ивент":
            await event_cmd(message)
        case _ if text.startswith("юз"):
            await use_cmd(message)
        case "предметы":
            await items_cmd(message)
        case "бабло":
            await message.reply(f"{COIN_EMOJI} Бабло: {user.coin}")
        case "статы":
            await stats_cmd(message)
        case "квест":
            await quest_cmd(message)
        case "погода":
            await weather_cmd(message)
        case "обменник":
            await exchanger_cmd(message)
        case _ if text.startswith("передать"):
            await transfer_cmd(message)
        case "собака":
            await dog_cmd(message)
        case _ if text.startswith("прайс"):
            await price_cmd(message)
        case "гайд":
            await guide_cmd(message)
        case "дом":
            await home_cmd(message)
        case "рынок":
            await market_cmd(message)
        case "достижения" | "ачивки":
            await achievements_cmd(message)
