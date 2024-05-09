from datetime import datetime
from typing import Optional, Union
from bson import ObjectId


class DictSerializable:
    def to_dict(self) -> dict:
        return self.__dict__

    @classmethod
    def from_dict(cls, dict_data: dict):
        instance = cls()
        instance.__dict__.update(dict_data)
        return instance


class UserModel(DictSerializable):
    def __init__(self, **kwargs) -> None:
        self._id: ObjectId
        self.id: int
        self.name: str
        self.username: Union[str, Optional[None]]
        self.vikicoin: int = 0
        self.rating: int = 0
        self.is_admin: bool = False
        self.is_banned: bool = False
        self.registered_at: datetime = datetime.utcnow()
        self.last_gift_time: datetime = datetime.utcnow()

        for k, v in kwargs.items():
            setattr(self, k, v)

    def __repr__(self):
        return f"{self.__class__.__name__} {self.name}"
