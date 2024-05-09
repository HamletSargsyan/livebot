from typing import Any, Generic, Type, TypeVar, Union
from pymongo import MongoClient
from pymongo.collection import Collection

from helpers.exceptions import NoResult
from config import DB_NAME, DB_URL
from database.models import UserModel


client = MongoClient(DB_URL)
db = client.get_database(DB_NAME)

users = db.get_collection("users")

T = TypeVar("T", UserModel, Any)  # NOTE: delete `Any` if you add new model


class BaseDB(Generic[T]):
    def __init__(self, collection: Collection, model: Type[T]):
        self.collection: Collection = collection
        self.model = model

    def add(self, **kwargs):
        return self.collection.insert_one(kwargs)

    def delete(self, **data):
        return self.collection.delete_one(data)

    def update(self, _id: Union[int, str], **data):
        return self.collection.update_one({"_id": _id}, {"$set": data})

    def get(self, **data):
        obj = self.collection.find_one(data)
        if not obj:
            raise NoResult
        return self.model(**obj)

    def get_all(self, **data):
        obj = self.collection.find(data)
        if not obj:
            return []
        return [self.model(**attrs) for attrs in obj]

    def check_exists(self, **data) -> bool:
        try:
            return self.get(**data) is not None
        except NoResult:
            return False


class DataBase:
    def __init__(self) -> None:
        self.users = BaseDB(users, UserModel)


database = DataBase()
