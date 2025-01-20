from typing import Final, Generic, Type, TypeVar

import redis
from bson import ObjectId
from cachetools import TTLCache
from pymongo import AsyncMongoClient, MongoClient
from pymongo.asynchronous.collection import AsyncCollection
from pymongo.collection import Collection

from config import config
from database.models import (
    AchievementModel,
    BaseModel,
    DailyGiftModel,
    DogModel,
    ExchangerModel,
    ItemModel,
    MarketItemModel,
    NotificationModel,
    PromoModel,
    QuestModel,
    UserModel,
)
from helpers.exceptions import NoResult

client = MongoClient(config.database.url, tz_aware=True)
async_client = AsyncMongoClient(config.database.url, tz_aware=True)

if config.database.name == "test":
    choice = input(f"Drop database `{config.database.name}`? [N/y] ")
    if choice == "y":
        client.drop_database(config.database.name)
        del choice

db = client.get_database(config.database.name)
async_db = async_client.get_database(config.database.name)


T = TypeVar("T", bound=BaseModel)


class BaseDB(Generic[T]):
    def __init__(self, collection_name: str, model: Type[T]):
        self.collection: Collection = db.get_collection(collection_name)
        self.async_collection: AsyncCollection = async_db.get_collection(collection_name)
        self.model = model

    def add(self, **kwargs):
        return self.collection.insert_one(kwargs)

    def delete(self, **data):
        return self.collection.delete_one(data)

    def update(self, _id: ObjectId, **data):
        return self.collection.update_one({"_id": _id}, {"$set": data})

    def get(self, **data) -> T:
        obj = self.collection.find_one(data)
        if not obj:
            raise NoResult
        return self.model.from_dict(obj)

    def get_all(self, **data) -> list[T]:
        obj = self.collection.find(data)
        if not obj:
            raise NoResult
        return [self.model.from_dict(attrs) for attrs in obj]

    def check_exists(self, **data) -> bool:
        try:
            return self.get(**data) is not None
        except NoResult:
            return False

    async def async_add(self, **kwargs):
        return await self.async_collection.insert_one(kwargs)

    async def async_delete(self, **data):
        return await self.async_collection.delete_one(data)

    async def async_update(self, _id: ObjectId, **data):
        return await self.async_collection.update_one({"_id": _id}, {"$set": data})

    async def async_get(self, **data) -> T:
        obj = await self.async_collection.find_one(data)
        if not obj:
            raise NoResult
        return self.model.from_dict(obj)

    async def async_get_all(self, **data) -> list[T]:
        obj = self.async_collection.find(data)
        if not obj:
            raise NoResult
        return [self.model.from_dict(attrs) for attrs in obj]

    async def async_check_exists(self, **data) -> bool:
        try:
            return await self.async_get(**data) is not None
        except NoResult:
            return False


class DataBase:
    def __init__(self) -> None:
        self.users = BaseDB("users", UserModel)
        self.items = BaseDB("items", ItemModel)
        self.promos = BaseDB("promos", PromoModel)
        self.quests = BaseDB("quests", QuestModel)
        self.exchangers = BaseDB("exchangers", ExchangerModel)
        self.dogs = BaseDB("dogs", DogModel)
        self.notifications = BaseDB("notifications", NotificationModel)
        self.market_items = BaseDB("market_items", MarketItemModel)
        self.daily_gifts = BaseDB("daily_gifts", DailyGiftModel)
        self.achievements = BaseDB("achievements", AchievementModel)


database: Final = DataBase()
redis_cache: Final = redis.from_url(config.redis.url)
cache: Final = TTLCache(maxsize=1, ttl=1800)
