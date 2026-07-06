from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal, Optional

import transliterate
from aiogram.types import CallbackQuery

from livebot.helpers.cache import cached
from livebot.helpers.enums import ItemRarity, ItemType


if TYPE_CHECKING:
    from livebot.database.models import UserModel


ChatIdType = int | str
UserActionType = Literal["walk", "work", "sleep", "game", "fishing"]


@dataclass(kw_only=True)
class ItemCraft:
    name: str
    quantity: int


@dataclass(kw_only=True)
class Item:
    name: str
    emoji: str
    desc: str
    rarity: ItemRarity
    type: ItemType = ItemType.STACKABLE
    is_quest_item: bool = False
    can_exchange: bool = False
    is_consumable: bool = False
    altnames: list[str] = field(default_factory=list)
    craft: Optional[list[ItemCraft]] = None
    effect: Optional[int] = None
    price: Optional[int] = None
    quest_coin: Optional[range] = None
    exchange_price: Optional[range] = None
    strength_reduction: Optional[tuple[float, float]] = None
    can_equip: bool = False

    @cached()
    def translit(self) -> str:
        return transliterate.translit(self.name, reversed=True)


@dataclass(kw_only=True)
class AchievementReward:
    name: str
    quantity: int


@dataclass(kw_only=True)
class Achievement:
    name: str
    emoji: str
    desc: str
    need: int
    reward: list[AchievementReward]

    @property
    def key(self) -> str:
        return self.name.strip().replace(" ", "-")

    def __str__(self) -> str:
        return f"{self.emoji} {self.name}"

    def check(self, user: "UserModel") -> bool:
        progress = user.achievements_info.progress.get(self.key, 0)
        return progress >= self.need

    @cached()
    def translit(self) -> str:
        return transliterate.translit(self.key, reversed=True)


@dataclass(kw_only=True)
class Mob:
    emoji: str
    name: str
    desc: str
    chance: float

    async def on_meet(self, query: CallbackQuery, user: "UserModel"):
        raise NotImplementedError

    @cached()
    def translit(self) -> str:
        return transliterate.translit(self.name, reversed=True)
