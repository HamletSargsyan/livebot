from datetime import datetime, timedelta, UTC
from typing import Any, Literal, Optional
from dataclasses import asdict, dataclass, field

from bson import ObjectId, Int64
from dacite import from_dict as _from_dict  # cspell: disable-line
from dateutil.relativedelta import relativedelta  # cspell: disable-line

from helpers.enums import ItemType, Locations
from helpers.exceptions import NoResult


def _utcnow():
    return datetime.now(UTC)


@dataclass
class BaseModel:
    def to_dict(self) -> dict:
        result = {}
        for key, value in asdict(self).items():
            if isinstance(value, bool):
                result[key] = value
            elif isinstance(value, int):
                result[key] = Int64(value)
            else:
                result[key] = value
        return result

    @classmethod
    def from_dict(cls, dict_data: dict[str, Any]):
        return _from_dict(cls, dict_data)


@dataclass(init=False)
class ItemModel(BaseModel):
    name: str


@dataclass
class CountableItemModel(ItemModel):
    quantity: int = 0


@dataclass
class UsableItemModel(ItemModel):
    is_equipped: bool = False
    usage: float = 100.0


ItemModelType = CountableItemModel | UsableItemModel


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
    expires: datetime
    _id: ObjectId = field(default_factory=ObjectId)
    owner: ObjectId = field(default_factory=ObjectId)


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
class Violation:
    reason: str
    type: Literal["warn", "mute", "ban", "permanent-ban"]
    date: datetime = field(default_factory=_utcnow)
    is_permanent: bool = False
    until_date: Optional[datetime] = None

    def __post_init__(self):
        if self.type == "permanent-ban":
            self.is_permanent = True
        elif self.type == "warn" and not self.until_date:
            self.until_date = _utcnow() + relativedelta(months=3)


@dataclass
class UserAction:
    type: Literal["street", "work", "sleep", "game"]
    end: datetime
    start: datetime = field(default_factory=_utcnow)


@dataclass
class ItemStorage:
    items: list[ItemModelType] = field(default_factory=list)

    def add(self, item: ItemModelType):
        self.items.append(item)

    def add_by_name(self, name: str) -> ItemModelType:
        from helpers.utils import get_item

        if get_item(name).type == ItemType.COUNTABLE:
            if self.check_exists(name):
                return self.find_one(name)
            item = CountableItemModel(name)
        else:
            item = UsableItemModel(name)

        self.add(item)
        return item

    def update(self, *items: ItemModelType):
        for item in items:
            self.add(item)

    def find(self, name: str, *, limit: Optional[int] = None):
        items = [item for item in self.items if item.name == name]

        if limit is not None:
            return items[:limit]
        return items

    def find_one(self, name: str) -> ItemModelType:
        items = self.find(name, limit=1)
        if items:
            return items[0]
        raise NoResult(name)

    def get_or_add(self, name: str) -> ItemModelType:
        if item := self.find_one(name):
            return item

        from helpers.utils import get_item

        if get_item(name).type == ItemType.COUNTABLE:
            item = CountableItemModel(name)
        else:
            item = UsableItemModel(name)

        self.add(item)
        return item

    def remove(self, item: ItemModelType) -> bool:
        self.items.remove(item)
        return True

    def remove_by_name(self, name: str) -> bool:
        if item := self.find_one(name):
            return self.remove(item)
        return False

    def check_exists(self, name: str) -> bool:
        return self.find_one(name) is not None

    def transfer(
        self, item: ItemModelType, from_user: "UserModel", to_user: "UserModel"
    ):
        from_user.inventory.remove(item)
        to_user.inventory.add(item)

    def transfer_by_name(self, name: str, to_user: "UserModel"):
        if item := self.find_one(name):
            to_user.inventory.add(item)
            self.remove(item)
            return True
        return False

    def __iter__(self):
        return iter(self.items)

    def __len__(self) -> int:
        return len(self.items)


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
    violations: list[Violation] = field(default_factory=list)
    coin: int = 0
    health: int = 100
    mood: int = 100
    hunger: int = 0
    fatigue: int = 0
    location: str = Locations.HOME.value
    action: Optional[UserAction] = None
    casino_win: int = 0
    casino_loose: int = 0
    new_quest_coin_quantity: int = 2
    max_items_count_in_market: int = 4
    luck: int = 1
    adverts_count: int = 0
    last_active_time: datetime = field(default_factory=_utcnow)
    achievement_progress: dict = field(default_factory=dict)
    accepted_rules: bool = False
    inventory: ItemStorage = field(default_factory=ItemStorage)


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
