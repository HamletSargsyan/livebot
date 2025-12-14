import difflib
import random
from typing import Optional, ParamSpec, TypeVar

from livebot.data.items.items import ITEMS
from livebot.datatypes import Item
from livebot.helpers.enums import ItemRarity
from livebot.helpers.exceptions import ItemNotFoundError
from livebot.helpers.utils import cached


P = ParamSpec("P")
T = TypeVar("T")

RARITY_WEIGHTS = {
    ItemRarity.COMMON: 60,
    ItemRarity.UNCOMMON: 25,
    ItemRarity.RARE: 10,
    ItemRarity.EPIC: 4,
    ItemRarity.LEGENDARY: 1,
}


@cached()
def get_item(name: str) -> Item:
    for item in ITEMS:
        if item.name == name:
            return item
        if name in item.altnames:
            return item
        if item.translit() == name:
            return item
        if difflib.get_close_matches(name, [item.name, item.translit(), *item.altnames]):
            return item
    raise ItemNotFoundError(name)


@cached()
def get_item_emoji(name: str) -> str:
    return get_item(name).emoji


def get_item_count_for_rarity(rarity: ItemRarity) -> int:
    match rarity:
        case ItemRarity.COMMON:
            quantity = random.randint(10, 20)
        case ItemRarity.UNCOMMON:
            quantity = random.randint(6, 8)
        case ItemRarity.RARE:
            quantity = random.randint(3, 5)
        case ItemRarity.EPIC:
            quantity = random.randint(1, 2)
        case ItemRarity.LEGENDARY:
            quantity = 1
        case _:
            raise NotImplementedError(f"Unknown rarity: {rarity}")
    return quantity


@cached(storage="disk")
def get_weights_for_items(items: list[Item]) -> list[int]:
    return [RARITY_WEIGHTS[item.rarity] for item in items]


def get_random_items(
    quantity: int,
    unique: bool = False,
    items: Optional[list[Item]] = None,
) -> list[Item]:
    items = items or ITEMS
    weights = get_weights_for_items(items)
    if unique:
        if quantity > len(items):
            raise ValueError("Cannot select more unique items than available in the list.")
        return random.sample(items, k=quantity)
    return random.choices(items, weights=weights, k=quantity)
