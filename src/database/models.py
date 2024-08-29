from datetime import datetime, timedelta, UTC
from typing import Optional
from bson import ObjectId, Int64
from dataclasses import dataclass, field, fields

from helpers.enums import ItemType, Locations


def _utcnow():
    return datetime.now(UTC)


@dataclass
class BaseModel:
    def to_dict(self) -> dict:
        result = {}
        for key, value in self.__dict__.items():
            if isinstance(value, int):
                result[key] = Int64(value)
            else:
                result[key] = value
        return result

    @classmethod
    def from_dict(cls, dict_data: dict):
        field_names = {f.name for f in fields(cls)}
        filtered_data = {
            key: value for key, value in dict_data.items() if key in field_names
        }
        return cls(**filtered_data)


@dataclass
class ItemModel(BaseModel):
    name: str
    quantity: int
    usage: Optional[float] = None
    is_equipped: bool = False
    _id: ObjectId = field(default_factory=ObjectId)
    owner: ObjectId = field(default_factory=ObjectId)

    def __post_init__(self):
        from helpers.utils import get_item

        _item = get_item(self.name)
        if _item.type == ItemType.USABLE and self.quantity > 1:
            raise ValueError(
                "Quantity must be 0 or 1 for items with type `ItemType.USABLE`"
            )
        if _item.type == ItemType.COUNTABLE and self.usage is not None:
            raise ValueError(
                "Usage must be `None` for items with type `ItemType.COUNTABLE`"
            )
        if not _item.can_equip and self.is_equipped:
            raise ValueError(f"Item {self.name} cannot be equipped")


@dataclass
class PromoModel(BaseModel):
    name: str
    is_used: bool = False
    usage_count: int = 1
    description: Optional[str] = None
    items: dict = field(default_factory=dict)
    users: list = field(default_factory=list)
    created_at: datetime = field(default_factory=_utcnow)
    _id: ObjectId = field(default_factory=ObjectId)


@dataclass
class QuestModel(BaseModel):
    name: str
    quantity: int = 1
    start_time: datetime = field(default_factory=_utcnow)
    xp: float = 1.0
    reward: int = 1
    owner: ObjectId = field(default_factory=ObjectId)
    _id: ObjectId = field(default_factory=ObjectId)


@dataclass
class ExchangerModel(BaseModel):
    item: str
    price: int
    _id: ObjectId = field(default_factory=ObjectId)
    owner: ObjectId = field(default_factory=ObjectId)
    expires: datetime = field(default_factory=lambda: _utcnow() + timedelta(days=1))


@dataclass
class DogModel(BaseModel):
    _id: ObjectId = field(default_factory=ObjectId)
    name: str = "Песик"
    level: int = 1
    xp: float = 0.0
    max_xp: int = 100
    health: int = 100
    hunger: int = 0
    fatigue: int = 0
    sleep_time: datetime = field(default_factory=_utcnow)
    owner: ObjectId = field(default_factory=ObjectId)


@dataclass
class NotificationModel(BaseModel):
    _id: ObjectId = field(default_factory=ObjectId)
    owner: ObjectId = field(default_factory=ObjectId)
    walk: bool = False
    work: bool = False
    sleep: bool = False
    game: bool = False
    health: bool = False
    mood: bool = False
    hunger: bool = False
    fatigue: bool = False


@dataclass
class UserModel(BaseModel):
    id: int
    name: str
    _id: ObjectId = field(default_factory=ObjectId)
    registered_at: datetime = field(default_factory=_utcnow)
    level: int = 1
    xp: float = 0.0
    max_xp: int = 155
    is_admin: bool = False
    is_banned: bool = False
    met_mob: bool = False
    ban_reason: Optional[str] = None
    ban_time: Optional[datetime] = None
    is_infinity_ban: Optional[bool] = None
    coin: int = 0
    health: int = 100
    mood: int = 100
    hunger: int = 0
    fatigue: int = 0
    location: str = Locations.HOME.value
    action_time: datetime = field(default_factory=_utcnow)
    state: Optional[str] = None
    casino_win: int = 0
    casino_loose: int = 0
    new_quest_coin_quantity: int = 2
    max_items_count_in_market: int = 4
    luck: int = 1
    adverts_count: int = 0
    last_active_time: datetime = field(default_factory=_utcnow)
    achievement_progress: dict = field(default_factory=dict)


@dataclass
class MarketItemModel(BaseModel):
    name: str
    price: int
    _id: ObjectId = field(default_factory=ObjectId)
    quantity: int = 0
    usage: Optional[float] = None
    published_at: datetime = field(default_factory=_utcnow)
    owner: ObjectId = field(default_factory=ObjectId)

    def __post_init__(self):
        from helpers.utils import get_item

        _item = get_item(self.name)
        if _item.type == ItemType.USABLE and self.quantity > 1:
            raise ValueError(
                "Quantity must be 0 or 1 for items with type `ItemType.USABLE`"
            )
        if _item.type == ItemType.COUNTABLE and self.usage is not None:
            raise ValueError(
                "Usage must be `None` for items with type `ItemType.COUNTABLE`"
            )


@dataclass
class DailyGiftModel(BaseModel):
    _id: ObjectId = field(default_factory=ObjectId)
    owner: ObjectId = field(default_factory=ObjectId)
    last_claimed_at: Optional[datetime] = None
    next_claimable_at: datetime = field(
        default_factory=lambda: _utcnow() + timedelta(days=1)
    )
    is_claimed: bool = False
    items: list = field(default_factory=list)
    streak: int = 0


@dataclass
class AchievementModel(BaseModel):
    name: str
    _id: ObjectId = field(default_factory=ObjectId)
    owner: ObjectId = field(default_factory=ObjectId)
    created_at: datetime = field(default_factory=_utcnow)
