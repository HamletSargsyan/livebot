from datetime import datetime, timedelta
from typing import Union
from bson import ObjectId

from helpers.enums import Locations


class DictSerializable:
    def to_dict(self) -> dict:
        return self.__dict__

    @classmethod
    def from_dict(cls, dict_data: dict):
        instance = cls()
        instance.__dict__.update(dict_data)
        return instance


class BaseModel(DictSerializable):
    def __init__(self, __exclude: list[str] = [], **kwargs) -> None:
        for k, v in kwargs.items():
            if k in __exclude:
                continue
            elif k in ["_id", "owner"]:
                setattr(self, k, ObjectId(v))
            else:
                setattr(self, k, v)


class ItemModel(BaseModel):
    def __init__(self, **kwargs) -> None:
        self._id: ObjectId
        self.name: str
        self.quantity: int = 0
        self.owner: ObjectId

        super().__init__(**kwargs)


class PromoModel(BaseModel):
    def __init__(self, **kwargs) -> None:
        self._id: ObjectId
        self.name: str
        self.is_used: bool = False
        self.usage_count: int = 1
        self.description: Union[str, None] = None
        self.items: dict
        self.users: list[int] = []
        self.created_at: datetime = datetime.utcnow()

        super().__init__(**kwargs)


class QuestModel(BaseModel):
    def __init__(self, **kwargs) -> None:
        self._id: ObjectId
        self.name: str
        self.quantity: int
        self.start_time: datetime
        self.xp: float
        self.reward: int
        self.owner: ObjectId

        super().__init__(**kwargs)


class ExchangerModel(BaseModel):
    def __init__(self, **kwargs) -> None:
        self._id: ObjectId
        self.expires: datetime = datetime.utcnow() + timedelta(days=1)
        self.item: str
        self.price: int
        self.owner: ObjectId

        super().__init__(**kwargs)


class DogModel(BaseModel):
    def __init__(self, **kwargs) -> None:
        self._id: ObjectId
        self.name: str = "Песик"
        self.level: int = 1
        self.xp: float = 0.0
        self.max_xp: float = 50.0
        self.health: int = 100
        self.hunger: int = 0
        self.fatigue: int = 0
        self.sleep_time: datetime
        # self.is_sleep: bool
        self.owner: ObjectId

        super().__init__(**kwargs)


class NotificationModel(BaseModel):
    def __init__(self, **kwargs) -> None:
        self._id: ObjectId
        self.owner: ObjectId
        self.walk: bool = False
        self.work: bool = False
        self.sleep: bool = False
        self.game: bool = False

        self.health: bool = False
        self.mood: bool = False
        self.hunger: bool = False
        self.fatigue: bool = False

        super().__init__(**kwargs)


class UserModel(BaseModel):
    def __init__(self, **kwargs) -> None:
        self._id: ObjectId
        self.id: int
        self.name: str
        self.registered_at: datetime = datetime.utcnow()
        self.level: int = 1
        self.xp: float = 0.0
        self.max_xp: float = 50.0
        self.is_admin: bool = False
        self.is_banned: bool = False
        self.met_mob: bool = False
        self.ban_reason: Union[str, None] = None
        self.ban_time: Union[datetime, None] = None
        self.is_infinity_ban: Union[bool, None] = None
        self.coin: int = 0
        self.health: int = 100
        self.mood: int = 100
        self.hunger: int = 0
        self.fatigue: int = 0
        self.location: str = Locations.HOME.value
        self.action_time: datetime = datetime.utcnow()
        self.state: Union[str, None] = None
        self.casino_win: int = 0
        self.casino_loose: int = 0
        self.new_quest_coin_quantity: int = 2
        self.max_items_count_in_market: int = 4
        self.luck: int = 1

        super().__init__(**kwargs)
        self.id = int(self.id)  # BUG: for fix bug: float id


class MarketItemModel(BaseModel):
    def __init__(self, **kwargs) -> None:
        self._id: ObjectId
        self.name: str
        self.price: int = 0
        self.quantity: int = 0
        self.published_at: datetime = datetime.utcnow()
        self.owner: ObjectId

        super().__init__(**kwargs)
