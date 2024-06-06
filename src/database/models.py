from typing import TypeVar, Generic, Type, Any
from datetime import datetime, timedelta
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


T = TypeVar("T")


class Field(Generic[T]):
    def __init__(
        self,
        type: Type[T],
        default: T | None = None,
        required: bool = False,
        nullable: bool = False,
    ) -> None:
        self._type = type
        self._default = default
        self._required = required
        self._nullable = nullable

    def __get__(self, instance: Any, owner: Type) -> T:
        if instance is None:
            return self  # type: ignore
        return instance.__dict__.get(self._name, self._default)

    def __set__(self, instance: Any, value: T) -> None:
        if not self._nullable and value is None:
            raise ValueError(f"{self._name} cannot be None")
        if value is not None and not isinstance(value, self._type):
            raise ValueError(
                f"Invalid type. Expected {self._type}, got {type(value)} for field {self._name}"
            )
        instance.__dict__[self._name] = value

    def __set_name__(self, owner: Type, name: str) -> None:
        self._name = name

    def __str__(self) -> str:
        return f"<Field type={self._type}, default={self._default}, required={self._required}, nullable={self._nullable}>"


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
    _id = Field(ObjectId)
    name = Field(str)
    quantity = Field(int, default=0)
    is_equiped = Field(bool, default=False)
    owner = Field(ObjectId)

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)


class PromoModel(BaseModel):
    _id = Field(ObjectId)
    name = Field(str)
    is_used = Field(bool, default=False)
    usage_count = Field(int, default=1)
    description = Field(str, nullable=True)
    items = Field(dict, default={})
    users = Field(list, default=[])
    created_at = Field(datetime, default=datetime.utcnow())

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)


class QuestModel(BaseModel):
    _id = Field(ObjectId)
    name = Field(str)
    quantity = Field(int, default=1)
    start_time = Field(datetime, default=datetime.utcnow())
    xp = Field(float, default=1.0)
    reward = Field(int, default=1)
    owner = Field(ObjectId)

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)


class ExchangerModel(BaseModel):
    _id = Field(ObjectId)
    expires = Field(datetime, default=datetime.utcnow() + timedelta(days=1))
    item = Field(str)
    price = Field(int)
    owner = Field(ObjectId)

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)


class DogModel(BaseModel):
    _id = Field(ObjectId)
    name = Field(str, default="Песик")
    level = Field(int, default=1)
    xp = Field(float, default=0.0)
    max_xp = Field(int)
    health = Field(int, default=100)
    hunger = Field(int, default=0)
    fatigue = Field(int, default=0)
    sleep_time = Field(datetime, default=datetime.utcnow())
    owner = Field(ObjectId)

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)


class NotificationModel(BaseModel):
    _id = Field(ObjectId)
    owner = Field(ObjectId)
    walk = Field(bool, default=False)
    work = Field(bool, default=False)
    sleep = Field(bool, default=False)
    game = Field(bool, default=False)

    health = Field(bool, default=False)
    mood = Field(bool, default=False)
    hunger = Field(bool, default=False)
    fatigue = Field(bool, default=False)

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)


class UserModel(BaseModel):
    _id = Field(ObjectId)
    id = Field(int)
    name = Field(str)
    registered_at = Field(datetime, default=datetime.utcnow())
    level = Field(int, default=1)
    xp = Field(float, default=0.0)
    max_xp = Field(int, default=155)
    is_admin = Field(bool, default=False)
    is_banned = Field(bool, default=False)
    met_mob = Field(bool, default=False)
    ban_reason = Field(str, nullable=True)
    ban_time = Field(datetime, nullable=True)
    is_infinity_ban = Field(bool, nullable=True)
    coin = Field(int, default=0)
    health = Field(int, default=100)
    mood = Field(int, default=100)
    hunger = Field(int, default=0)
    fatigue = Field(int, default=0)
    location = Field(str, default=Locations.HOME.value)
    action_time = Field(datetime, default=datetime.utcnow())
    state = Field(str, nullable=True)
    casino_win = Field(int, default=0)
    casino_loose = Field(int, default=0)
    new_quest_coin_quantity = Field(int, default=2)
    max_items_count_in_market = Field(int, default=4)
    luck = Field(int, default=1)

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)


class MarketItemModel(BaseModel):
    _id = Field(ObjectId)
    name = Field(str)
    price = Field(int, default=0)
    quantity = Field(int, default=0)
    published_at = Field(datetime, default=datetime.utcnow())
    owner = Field(ObjectId)

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
