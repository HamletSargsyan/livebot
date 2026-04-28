import random
from contextlib import suppress
from datetime import timedelta

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.scene import ScenesManager
from aiogram.types import CallbackQuery, Message
from bson import ObjectId

from livebot.consts import MARKET_ITEMS_LIST_MAX_ITEMS_COUNT
from livebot.core.player_actions import (
    fishing_action,
    game_action,
    sleep_action,
    walk_action,
    work_action,
)
from livebot.data.achievements.utils import get_achievement
from livebot.data.items.items import ITEMS
from livebot.data.items.utils import get_item, get_item_count_for_rarity, get_random_items
from livebot.database.models import MarketItemModel, UserModel
from livebot.handlers.scenes.market import AddMarketItemMainScene
from livebot.helpers.callback_factory import (
    AchievementsCallback,
    ChestCallback,
    CraftCallback,
    DailyGiftCallback,
    HomeCallback,
    MarketCallback,
    QuestCallback,
    RulesCallback,
    ShopCallback,
    TraderCallback,
    TransferCallback,
    UseCallback,
)
from livebot.helpers.datetime_utils import utcnow
from livebot.helpers.enums import ItemRarity
from livebot.helpers.exceptions import ItemNotFoundError, NoResult
from livebot.helpers.localization import t
from livebot.helpers.markups import InlineMarkup
from livebot.helpers.player_utils import (
    check_user_subscription,
    get_available_items_for_use,
    transfer_item,
)
from livebot.helpers.stickers import Stickers
from livebot.helpers.utils import batched, pretty_float, pretty_int


router = Router()


@router.callback_query(ShopCallback.filter())
async def shop_callback(query: CallbackQuery, callback_data: ShopCallback):
    if callback_data.user_id != query.from_user.id:
        return

    user = await UserModel.get_async(id=query.from_user.id)

    try:
        item = get_item(callback_data.item_name)
    except ItemNotFoundError as e:
        await query.answer(t("item-not-exist", item_name=str(e)), show_alert=True)
        return

    assert item.price  # for linters
    quantity = callback_data.quantity
    price = item.price * quantity

    if user.coin < price:
        await query.answer(text=t("item-not-enough", item_name="бабло"), show_alert=True)
        return

    user.inventory.add(item.name, quantity)

    user.coin -= price

    assert isinstance(query.message, Message)

    await query.message.reply_to_message.reply(
        t("shop.buy-item", quantity=quantity, item_name=item.name, price=price),
    )

    await user.update_async()


@router.callback_query(CraftCallback.filter())
async def craft_callback(query: CallbackQuery, callback_data: CraftCallback):
    if callback_data.user_id != query.from_user.id:
        return

    user = await UserModel.get_async(id=query.from_user.id)

    assert callback_data.item_name

    try:
        item = get_item(callback_data.item_name)
    except ItemNotFoundError as e:
        await query.answer(t("item-not-exist", item_name=str(e)), show_alert=True)
        return

    assert item.craft  # for linters

    quantity = callback_data.quantity

    for craft in item.craft:
        try:
            user_item = user.inventory.get(craft.name)
            if user_item.quantity < craft.quantity * quantity:
                raise NoResult(craft.name)
        except NoResult:
            await query.answer(t("item-not-enough", item_name=craft.name))
            return

        user.inventory.remove(user_item.name, craft.quantity * quantity)

    user.inventory.add(item.name, quantity)

    xp = random.uniform(5.0, 10.0)

    if random.randint(1, 100) < user.luck:
        xp += random.uniform(2.3, 6.7)

    user.xp += xp
    await user.check_status()
    await user.update_async()

    assert isinstance(query.message, Message)

    with suppress(TelegramBadRequest):
        await query.message.edit_reply_markup(reply_markup=InlineMarkup.craft_main(quantity, user))

    await query.message.reply_to_message.reply(
        t(
            "craft.craft-item",
            quantity=quantity,
            item_name=item.name,
            xp=xp,
        )
    )


@router.callback_query(TransferCallback.filter())
async def transfer_callback(query: CallbackQuery, callback_data: TransferCallback):
    if callback_data.user_id != query.from_user.id:
        return

    user = await UserModel.get_async(id=query.from_user.id)
    target_user = await UserModel.get_async(id=callback_data.to_user_id)

    mess = transfer_item(user, target_user, ObjectId(callback_data.item_oid))

    await user.update_async()
    await target_user.update_async()

    await query.message.answer(mess)


@router.callback_query(UseCallback.filter())
async def use_callback(query: CallbackQuery, callback_data: UseCallback):
    if callback_data.user_id != query.from_user.id:
        return

    user = await UserModel.get_async(id=query.from_user.id)

    try:
        user_item = user.inventory.get_by_id(id=ObjectId(callback_data.item_oid))
    except NoResult:
        await query.answer(t("item-not-found-in-inventory", item_name="?????"))
        return

    if user_item.quantity <= 0:
        await query.answer(t("item-not-enough", item_name=user_item.name))
        return

    item = get_item(user_item.name)

    match item.name:
        case "трава" | "буханка" | "сэндвич" | "пицца" | "тако" | "суп" | "рыба":
            user.hunger += item.effect  # type: ignore
            mess = t("use.hunger", item_name=item.name, effect=item.effect)
        case "буст":
            xp = random.randint(100, 150)
            user.xp += xp
            mess = t("use.boost", item_name=item.name, xp=xp)
        case "бокс":
            num_items_to_get = random.randint(1, 3)
            items = ""

            for item_to_get in get_random_items(num_items_to_get, unique=True):
                quantity = get_item_count_for_rarity(item_to_get.rarity)

                items += f"+ {pretty_int(quantity)} {item_to_get.name} {item_to_get.emoji}\n"
                if item_to_get.name == "бабло":
                    user.coin += quantity
                else:
                    user.inventory.add(item_to_get.name, quantity)
            mess = t("use.box-opened", items=items)
        case "энергос" | "чай":
            user.fatigue += item.effect  # type: ignore
            mess = t("use.fatigue", item_name=item.name, effect=item.effect)
        case "пилюля":
            await query.message.reply(t("under-development"))
            return
        case "хелп":
            user.health += item.effect  # type: ignore
            mess = t("use.health", item_name=item.name, effect=item.effect)
        case "фиксоманчик":
            await query.message.reply(t("under-development"))
            return
        case "водка":
            user.fatigue = 100
            user.health -= item.effect  # type: ignore
            mess = t("use.vodka", item_name=item.name, effect=item.effect)
        case "велик":
            if not user.action or user.action.type != "walk":
                await query.message.reply("Ты не гуляешь")  # TODO: add translation
                return
            minutes = random.randint(10, 45)
            user.action.end -= timedelta(minutes=minutes)
            mess = t("use.bike", item_name=item.name, minutes=minutes)
        case "клевер-удачи":
            user.luck += item.effect  # type: ignore
            mess = t("use.luck", item_name=item.name, effect=item.effect)
        case "конфета":
            user.hunger += item.effect  # type: ignore
            user.fatigue += item.effect  # type: ignore
            mess = t("use.candy", item_name=item.name, effect=item.effect)
        case _:
            raise NotImplementedError(item.name)

    user.inventory.remove(user_item.name, 1, id=user_item.id)
    await user.check_status(chat_id=query.message.chat.id)
    await user.update_async()

    items = get_available_items_for_use(user)

    if items:  # pylint: disable=duplicate-code
        key = "use.available-items"
    else:
        key = "use.not-available-items"

    assert isinstance(query.message, Message)
    await query.message.edit_text(
        t(key),
        reply_markup=InlineMarkup.use(items, user),
    )
    await query.message.reply(mess)


@router.callback_query(QuestCallback.filter())
async def quest_callback(query: CallbackQuery, callback_data: QuestCallback):
    if callback_data.user_id != query.from_user.id:
        return

    user = await UserModel.get_async(id=query.from_user.id)

    assert isinstance(query.message, Message)  # for linters
    if callback_data.action == "skip":
        if user.coin < user.new_quest_coin_quantity:
            await query.answer(t("item-not-enough", item_name="бабло"))
            return
        user.coin -= user.new_quest_coin_quantity
        user.new_quest_coin_quantity += random.randint(10, 20)
        user.new_quest()
        await query.message.delete()
        await user.update_async()
        await query.answer(t("quest.skipped"), show_alert=True)
        return

    if not user.quest.is_done:
        await query.answer(t("quest.quest-not-completed"))
        return

    for name, quantity in user.quest.needed_items.items():
        user.inventory.remove(name, quantity)

    user.coin += user.quest.reward
    user.xp += user.quest.xp
    old_quest = user.quest
    user.new_quest()
    user.achievements_info.incr_progress("квестоман")

    await user.update_async()
    await query.message.delete()
    await query.message.answer_sticker(Stickers.quest)
    await query.message.reply_to_message.reply(t("quest.complete", quest=old_quest))


@router.callback_query(HomeCallback.filter())
async def home_callback(query: CallbackQuery, callback_data: HomeCallback):
    if callback_data.user_id != query.from_user.id:
        return

    user = await UserModel.get_async(id=query.from_user.id)

    assert isinstance(query.message, Message)  # for liners

    match callback_data.action:
        case "actions":
            await query.message.edit_text(
                t("home.actions-choice"),
                reply_markup=InlineMarkup.home_actions_choice(user),
            )
        case "main-menu":
            await query.message.edit_text(
                t("home.main"),
                reply_markup=InlineMarkup.home_main(user),
            )
        case "walk":
            await walk_action(query, user)
        case "work":
            await work_action(query, user)
        case "sleep":
            await sleep_action(query, user)
        case "game":
            await game_action(query, user)
        case "fishing":
            await fishing_action(query, user)


@router.callback_query(TraderCallback.filter())
async def trader_callback(query: CallbackQuery, callback_data: TraderCallback):
    if callback_data.user_id != query.from_user.id:
        return

    user = await UserModel.get_async(id=query.from_user.id)

    assert isinstance(query.message, Message)  # for liners

    if callback_data.action == "leave":
        await query.message.delete()
        await query.answer(t("mobs.trader.leave"), show_alert=True)
        return

    assert callback_data.item_name  # for linters
    assert callback_data.price  # for linters
    assert callback_data.quantity  # for linters

    item = get_item(callback_data.item_name)

    if user.coin < callback_data.price:
        await query.answer(
            t("item-not-enough", item_name="бабло"),
            show_alert=True,
        )
        return

    user.coin -= callback_data.price
    user.inventory.add(item.name, callback_data.quantity)
    await user.update_async()
    await query.message.delete()
    await query.message.answer(
        t(
            "mobs.trader.trade",
            user=user,
            item=item,
            quantity=callback_data.quantity,
            price=callback_data.price,
        )
    )


@router.callback_query(ChestCallback.filter())
async def chest_callback(query: CallbackQuery, callback_data: ChestCallback):
    if callback_data.user_id != query.from_user.id:
        return

    user = await UserModel.get_async(id=query.from_user.id)

    assert isinstance(query.message, Message)  # for liners

    if callback_data.action == "leave":
        await query.message.delete()
        await query.answer(t("mobs.chest.leave"), show_alert=True)
        return

    try:
        key_item = user.inventory.get("ключ")
    except NoResult:
        await query.answer(t("item-not-found-in-inventory", item_name="ключ"), show_alert=True)
        return

    items = ""
    items_quantity = random.randint(2, 3)
    available_items = list(
        filter(lambda i: i.rarity in (ItemRarity.COMMON, ItemRarity.UNCOMMON), ITEMS)
    )
    available_items = get_random_items(items_quantity, items=available_items)

    for item in available_items:
        quantity = get_item_count_for_rarity(item.rarity)
        if item.name == "бабло":
            user.coin += quantity
        else:
            user.inventory.add(item.name, quantity)

        items += f"+ {pretty_int(quantity)} {item.name} {item.emoji}\n"

    user.inventory.remove(key_item.name, 1)
    user.achievements_info.incr_progress("кладоискатель")
    await user.update_async()

    await query.message.answer(t("mobs.chest.open", user=user, items=items))
    await query.message.delete()


@router.callback_query(AchievementsCallback.filter())
async def achievements_callback(query: CallbackQuery, callback_data: AchievementsCallback):
    if callback_data.user_id != query.from_user.id:
        return

    user = await UserModel.get_async(id=query.from_user.id)

    achievement = get_achievement(callback_data.achievement_name)
    user_achievement = user.achievements_info.get(achievement.name)

    await query.answer(
        t(
            "achievements.info",
            achievement=achievement,
            user_achievement=user_achievement,
        ),
        show_alert=True,
    )


@router.callback_query(DailyGiftCallback.filter())
async def daily_gift_callback(query: CallbackQuery, callback_data: DailyGiftCallback):
    if callback_data.user_id != query.from_user.id:
        return

    user = await UserModel.get_async(id=query.from_user.id)

    if not await check_user_subscription(user):
        await query.answer(t("subscription-required"), show_alert=True)
        return

    assert isinstance(query.message, Message)  # for liners

    if user.daily_gift.next_claim_available_at <= utcnow():
        user.new_daily_gift()
        await user.update_async()

    if user.daily_gift.is_claimed:
        await query.answer(
            t("daily-gift.already-claimed", daily_gift=user.daily_gift), show_alert=True
        )

        await query.message.edit_reply_markup(reply_markup=InlineMarkup.daily_gift(user))
        return

    if not user.daily_gift.last_claimed_at:
        user.daily_gift.last_claimed_at = utcnow()

    if (
        user.daily_gift.last_claimed_at
        and user.daily_gift.last_claimed_at.date() == (utcnow() - timedelta(days=1)).date()
    ):
        user.daily_gift.streak += 1
    else:
        user.daily_gift.streak = 1
    user.daily_gift.last_claimed_at = utcnow()
    user.daily_gift.is_claimed = True

    items = ""

    for item_name, quantity in user.daily_gift.items.items():
        item = get_item(item_name)

        items += f"+{pretty_int(quantity)} {item.name} {item.emoji}\n"
        if item_name == "бабло":
            user.coin += quantity
        else:
            user.inventory.add(item.name, quantity)

    user.notification_status.daily_gift = False
    await user.update_async()

    mess = t("daily-gift.claim", user=user, items=items)

    await query.message.answer(mess)
    await query.message.edit_reply_markup(reply_markup=InlineMarkup.daily_gift(user))


@router.callback_query(MarketCallback.filter(F.action != "select-item"))
async def market_callback(
    query: CallbackQuery,
    callback_data: MarketCallback,
    scenes: ScenesManager,
):
    if callback_data.user_id != query.from_user.id:
        return

    user = await UserModel.get_async(id=query.from_user.id)

    assert isinstance(query.message, Message)  # for linters

    match callback_data.action:
        case "view":
            assert callback_data.current_page is not None  # for linters
            item = await MarketItemModel.get_async(oid=callback_data.item_oid)

            await query.message.edit_text(
                t(
                    "market.item-info",
                    item=item,
                ),
                reply_markup=InlineMarkup.market_item_view(callback_data.current_page, item, user),
            )
        case "goto":
            assert callback_data.current_page is not None  # for linters
            items = await MarketItemModel.get_all_async()
            page = callback_data.current_page
            max_page = len(list(batched(items, MARKET_ITEMS_LIST_MAX_ITEMS_COUNT)))
            await query.message.edit_text(
                t("market.main", current_page=page + 1, max_page=max_page),
                reply_markup=InlineMarkup.market_main(page, user),
            )
        case "buy":
            item = await MarketItemModel.get_async(oid=callback_data.item_oid)

            if item.owner == user.oid:
                return  # TODO: Add message

            if user.coin < item.price:
                await query.answer(t("item-not-enough", item_name="бабло"))
                return

            user.coin -= item.price
            usage_text = ""
            if item.usage:
                usage_text = f"({pretty_float(item.usage)}%)"
                user.inventory.add(item.name, item.quantity, item.usage)
            else:
                user.inventory.add(item.name, item.quantity)

            await item.delete_async()
            await user.update_async()

            assert callback_data.current_page is not None  # for linters
            items = await MarketItemModel.get_all_async()
            page = callback_data.current_page
            max_page = len(list(batched(items, MARKET_ITEMS_LIST_MAX_ITEMS_COUNT)))
            await query.message.edit_text(
                t("market.main", current_page=page + 1, max_page=max_page),
                reply_markup=InlineMarkup.market_main(page, user),
            )

            await query.message.answer(t("market.buy-item", user=user, usage=usage_text, item=item))
            await query.bot.send_message(
                item.owner.id,
                t("market.sold-item", user=user, usage=usage_text, item=item),
            )
        case "back" | "next":
            assert callback_data.current_page is not None
            items = await MarketItemModel.get_all_async()
            page = callback_data.current_page
            max_page = len(list(batched(items, MARKET_ITEMS_LIST_MAX_ITEMS_COUNT)))
            if callback_data.action == "back":
                page -= 1
            else:
                page += 1

            page = max(0, min(max_page - 1, page))

            with suppress(TelegramBadRequest):
                await query.message.edit_text(
                    t("market.main", current_page=page + 1, max_page=max_page),
                    reply_markup=InlineMarkup.market_main(page, user),
                )
        case "kiosk":
            assert callback_data.current_page is not None

            await query.message.edit_text(
                t("market.kiosk"),
                reply_markup=InlineMarkup.market_kiosk(callback_data.current_page, user),
            )
        case "add":
            await scenes.enter(AddMarketItemMainScene)
        case "delete":
            assert callback_data.item_oid  # for linters
            item = await MarketItemModel.get_async(oid=callback_data.item_oid)

            if item.usage:
                user.inventory.add(item.name, item.quantity, item.usage)
            else:
                user.inventory.add(item.name, item.quantity)

            await item.delete_async()
            await user.update_async()

            await query.answer(t("market.item-removed", item=item), show_alert=True)

            await query.message.edit_reply_markup(
                reply_markup=InlineMarkup.market_my_items(user),
            )
        case "my-items":
            await query.message.edit_text(
                t("market.my-items"),
                reply_markup=InlineMarkup.market_my_items(user),
            )


@router.callback_query(RulesCallback.filter())
async def rules_callback(query: CallbackQuery, callback_data: RulesCallback):
    assert isinstance(query.message, Message)
    await query.message.delete()

    user = await UserModel.get_async(id=callback_data.user_id)

    user.accepted_rules = True
    await user.update_async()
