import random
from abc import ABC, abstractmethod
from typing import Optional

from aiogram.types import Message
from telebot.util import quick_markup

from helpers.utils import get_item_emoji

from base.items import ITEMS

from database.models import UserModel
from helpers.enums import ItemRarity


class BaseMob(ABC):
    def __init__(
        self,
        name: str,
        chance: float,
        message: Optional[Message] = None,
        user: Optional[UserModel] = None,
    ) -> None:
        self.name = name
        self.chance = chance
        self.message = message
        self.user = user

    @abstractmethod
    async def on_meet(self):
        raise NotImplementedError

    def init(self, user: UserModel, message: Message):
        self.user = user
        self.message = message


# ---------------------------------------------------------------------------- #


class Dog(BaseMob):
    def __init__(self) -> None:
        super().__init__("псина", 7.3)

        self.quantity = random.randint(4, 10)

    async def on_meet(self):
        if not self.user or not self.message:
            return
        mess = "Привет дружок, хочешь подружится?\n\n" f"Я хочу {self.quantity} 🦴"

        markup = quick_markup(
            {
                "Подружится": {"callback_data": f"dog friend {self.quantity} {self.user.id}"},
                "Уйти": {"callback_data": f"dog leave {self.user.id}"},
            }
        )

        await self.message.edit_text(mess, reply_markup=markup)


class Trader(BaseMob):
    def __init__(self):
        super().__init__("торговец", 5.2)
        self.items = [item for item in ITEMS if item.rarity == ItemRarity.COMMON]
        while True:
            self.item = random.choice(self.items)
            if self.item.price:
                break
        self.quantity = random.randint(2, 10)
        self.price = self.item.price * self.quantity

    async def on_meet(self):
        if not self.user or not self.message:
            return
        mess = (
            "<b>👳‍♂️ Торговец</b>\n\n"
            "Эй дружок, у меня для тебя есть выгодное предложение\n"
            f"Даю {self.quantity} {self.item.emoji} {self.item.name} за {self.price} {get_item_emoji('бабло')}"
        )

        markup = quick_markup(
            {
                "Обменять": {
                    "callback_data": f"trader trade {self.item.translit()} {self.quantity} {self.price} {self.user.id}"
                },
                "Отказаться": {"callback_data": f"trader leave {self.user.id}"},
            }
        )

        await self.message.edit_text(mess, reply_markup=markup)


class Chest(BaseMob):
    def __init__(self):
        super().__init__("сундук", 1.3)

    async def on_meet(self):
        if not self.user or not self.message:
            return
        mess = "<b>Сундук</b>\n\n" "- Ой а что это такое...?"
        markup = quick_markup(
            {
                "Открыть": {"callback_data": f"chest open {self.user.id}"},
                "Уйти": {"callback_data": f"chest leave {self.user.id}"},
            }
        )

        await self.message.edit_text(mess, reply_markup=markup)


# ---------------------------------------------------------------------------- #


def generate_mob():
    mob_types = [Dog, Trader, Chest]

    # now = datetime.datetime.now()
    # current_hour = now.hour

    # if 21 <= current_hour or current_hour <= 6:  # Ночь (с 21:00 до 6:00)
    #     mob_types = []
    # else:  # День (с 6:00 до 21:59)
    #     mob_types = []

    mob = random.choice(mob_types)
    chance = random.uniform(1, 10)

    if mob.chance <= chance:
        return mob()
