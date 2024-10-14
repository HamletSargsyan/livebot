from typing import Final, Generic, Type, TypeVar

from bson import ObjectId
from pymongo import MongoClient
from pymongo.collection import Collection

import redis

from helpers.exceptions import NoResult
from config import config
from database.models import (
    AchievementModel,
    MarketItemModel,
    NotificationModel,
    UserModel,
    ItemModel,
    PromoModel,
    QuestModel,
    ExchangerModel,
    DogModel,
    DailyGiftModel,
)


client = MongoClient(config.database.url, tz_aware=True)

if config.database.name == "test":
    choice = input(f"Drop database `{config.database.name}`? [N/y] ")
    if choice == "y":
        client.drop_database(config.database.name)
        del choice

db = client.get_database(config.database.name)

users = db.get_collection("users")
items = db.get_collection("items")
promos = db.get_collection("promos")
quests = db.get_collection("quests")
exchangers = db.get_collection("exchangers")
dogs = db.get_collection("dogs")
notifications = db.get_collection("notifications")
market_items = db.get_collection("market_items")
daily_gifts = db.get_collection("daily_gifts")
achievements = db.get_collection("achievements")


T = TypeVar(
    "T",
    UserModel,
    ItemModel,
    PromoModel,
    QuestModel,
    ExchangerModel,
    DogModel,
    NotificationModel,
    MarketItemModel,
    DailyGiftModel,
    AchievementModel,
)


class BaseDB(Generic[T]):
    def __init__(self, collection: Collection, model: Type[T]):
        self.collection: Collection = collection
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


class DataBase:
    def __init__(self) -> None:
        self.users = BaseDB(users, UserModel)
        self.items = BaseDB(items, ItemModel)
        self.promos = BaseDB(promos, PromoModel)
        self.quests = BaseDB(quests, QuestModel)
        self.exchangers = BaseDB(exchangers, ExchangerModel)
        self.dogs = BaseDB(dogs, DogModel)
        self.notifications = BaseDB(notifications, NotificationModel)
        self.market_items = BaseDB(market_items, MarketItemModel)
        self.daily_gifts = BaseDB(daily_gifts, DailyGiftModel)
        self.achievements = BaseDB(achievements, AchievementModel)


database: Final = DataBase()
redis_cache: Final = redis.from_url(config.redis.url)
