from typing import Generic, Type, TypeVar
from bson import ObjectId
from pymongo import MongoClient
from pymongo.collection import Collection

from helpers.exceptions import NoResult
from config import DB_NAME, DB_URL
from database.models import (
    NotificationModel,
    UserModel,
    ItemModel,
    PromoModel,
    QuestModel,
    ExchangerModel,
    DogModel,
)


client = MongoClient(DB_URL)

if DB_NAME == "test":
    choice = input(f"Drop database `{DB_NAME}`? [N/y]")
    if choice == "y":
        client.drop_database(DB_NAME)
        del choice

db = client.get_database(DB_NAME)

users = db.get_collection("users")
items = db.get_collection("items")
promos = db.get_collection("promos")
quests = db.get_collection("quests")
exchangers = db.get_collection("exchangers")
dogs = db.get_collection("dogs")
notifications = db.get_collection("notifications")


T = TypeVar(
    "T",
    UserModel,
    ItemModel,
    PromoModel,
    QuestModel,
    ExchangerModel,
    DogModel,
    NotificationModel,
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

    def get(self, **data):
        obj = self.collection.find_one(data)
        if not obj:
            raise NoResult
        return self.model(**obj)

    def get_all(self, **data):
        obj = self.collection.find(data)
        if not obj:
            raise NoResult
        return [self.model(**attrs) for attrs in obj]

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


database = DataBase()
