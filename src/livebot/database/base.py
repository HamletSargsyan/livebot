from dataclasses import dataclass, field, fields
from typing import Any, ClassVar, Required, Self, TypedDict

from bson import ObjectId
from mashumaro import DataClassDictMixin, field_options
from mashumaro.config import BaseConfig
from mashumaro.types import Discriminator, SerializationStrategy
from pymongo import AsyncMongoClient, MongoClient
from pymongo.asynchronous.collection import AsyncCollection
from pymongo.collection import Collection

from livebot.cli import ARGS
from livebot.config import config as app_config
from livebot.consts import EMPTY_OBJECTID
from livebot.helpers.exceptions import AlreadyExists, NoResult


_client_options = {
    "host": app_config.database.url,
    "tz_aware": True,
}


sync_client = MongoClient(**_client_options)
async_client = AsyncMongoClient(**_client_options)

sync_db = sync_client.get_database(app_config.database.name)
async_db = async_client.get_database(app_config.database.name)


if not ARGS.no_interactive and (app_config.general.debug and app_config.database.name == "dev"):
    choice = input(f"Drop database `{app_config.database.name}`? [N/y] ")
    if choice == "y":
        sync_client.drop_database(app_config.database.name)


class ModelSettings(TypedDict):
    collection_name: Required[str]


class ObjectIdSerializationStrategy(SerializationStrategy):
    def serialize(self, value: ObjectId) -> str:
        return str(value)

    def deserialize(self, value: str) -> ObjectId:
        return ObjectId(value)


@dataclass
class SubModel(DataClassDictMixin):
    class Config(BaseConfig):
        serialize_by_alias = True
        allow_deserialization_not_by_alias = True
        serialization_strategy = {  # noqa
            ObjectId: ObjectIdSerializationStrategy(),
        }
        discriminator = Discriminator(
            include_subtypes=True,
        )


@dataclass(kw_only=True)
class BaseModel(SubModel):
    oid: ObjectId = field(default=EMPTY_OBJECTID, metadata=field_options(alias="_id"))

    __settings__: ClassVar[ModelSettings]
    sync_collection: ClassVar[Collection]
    async_collection: ClassVar[AsyncCollection]

    def __init_subclass__(cls, **kwargs):
        if not cls.__name__.endswith("Model"):
            raise TypeError("Subclass name must end with 'Model'")
        cls._setup_model()
        return super().__init_subclass__(**kwargs)

    def __post_init__(self):
        if not hasattr(self, "oid"):
            self.oid = EMPTY_OBJECTID

        self._setup_model()

    @classmethod
    def __post_deserialize__(cls, obj: Self):  # pyright: ignore
        if hasattr(obj, "__post_init__"):
            obj.__post_init__()
        return obj

    @classmethod
    def _setup_model(cls):
        if not hasattr(cls, "sync_collection"):
            cls.sync_collection = sync_db.get_collection(cls.__settings__["collection_name"])
        if not hasattr(cls, "async_collection"):
            cls.async_collection = async_db.get_collection(cls.__settings__["collection_name"])

    @classmethod
    def _handle_options(cls, options: dict[str, Any]) -> dict[str, Any]:
        if "oid" in options:
            options["_id"] = options.pop("oid")

            if not isinstance(options["_id"], ObjectId):
                options["_id"] = ObjectId(options["_id"])
        return options

    def clone(self) -> Self:
        return self.__class__.from_dict(self.to_dict())

    @classmethod
    def get(cls, **options) -> Self:
        cls._setup_model()
        options = cls._handle_options(options)
        obj = cls.sync_collection.find_one(options)

        if not obj:
            raise NoResult
        return cls.from_dict(obj)

    @classmethod
    def get_all(cls, **options) -> list[Self]:
        cls._setup_model()
        options = cls._handle_options(options)
        objs = cls.sync_collection.find(options)

        if not objs:
            return []
        return [cls.from_dict(obj) for obj in objs]

    @classmethod
    def check_exists(cls, **options) -> bool:
        cls._setup_model()
        try:
            cls.get(**options)
            return True
        except NoResult:
            return False

    def add(self) -> None:
        if hasattr(self, "oid") and self.oid != EMPTY_OBJECTID:
            raise AlreadyExists
        dct = self.to_dict()
        del dct["_id"]
        result = self.sync_collection.insert_one(dct)
        self.oid = result.inserted_id
        assert self.oid

    def update(self) -> None:
        dct = self.to_dict()
        dct.pop("_id", None)
        self.sync_collection.update_one({"_id": self.oid}, {"$set": dct})

    def delete(self) -> None:
        self.sync_collection.delete_one({"_id": self.oid})

    def fetch(self) -> None:
        updated_instance = self.get(oid=self.oid)
        for field_ in fields(self):
            setattr(self, field_.name, getattr(updated_instance, field_.name))

    async def delete_async(self) -> None:
        await self.async_collection.delete_one({"_id": self.oid})

    async def update_async(self) -> None:
        dct = self.to_dict()
        dct.pop("_id", None)
        await self.async_collection.update_one({"_id": self.oid}, {"$set": dct})

    async def add_async(self) -> None:
        if hasattr(self, "oid") and self.oid != EMPTY_OBJECTID:
            raise AlreadyExists
        dct = self.to_dict()
        del dct["_id"]
        result = await self.async_collection.insert_one(dct)
        self.oid = result.inserted_id

        assert self.oid

    @classmethod
    async def check_exists_async(cls, **options) -> bool:
        cls._setup_model()
        try:
            await cls.get_async(**options)
            return True
        except NoResult:
            return False

    @classmethod
    async def get_all_async(cls, **options) -> list[Self]:
        cls._setup_model()
        options = cls._handle_options(options)
        objs = cls.async_collection.find(options)
        objs = await objs.to_list(length=None)

        if not objs:
            return []

        return [cls.from_dict(obj) for obj in objs]

    @classmethod
    async def get_async(cls, **options) -> Self:
        cls._setup_model()
        options = cls._handle_options(options)
        obj = await cls.async_collection.find_one(options)

        if not obj:
            raise NoResult
        return cls.from_dict(obj)

    async def fetch_async(self) -> None:
        updated_instance = await self.get_async(oid=self.oid)
        for field_ in fields(self):
            setattr(self, field_.name, getattr(updated_instance, field_.name))
