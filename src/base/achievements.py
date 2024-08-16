from typing import Final

from helpers.datatypes import Achievement


ACHIEVEMENTS: Final[list[Achievement]] = [
    Achievement(
        name="работяга",
        emoji="💼",
        desc="поработай 10 раз",
        need=10,
        reward={
            "бабло": 10_000,
        },
    ),
    Achievement(
        name="бродяга",
        emoji="🚶",
        desc="погуляй 10 раз",
        need=10,
        reward={
            "бокс": 2,
        },
    ),
    Achievement(
        name="сонный",
        emoji="💤",
        desc="поспи 15 раз",
        need=15,
        reward={
            "энергос": 10,
        },
    ),
    Achievement(
        name="игроман",
        emoji="🎮",
        desc="поиграй 20 раз",
        need=20,
        reward={
            "бокс": 3,
        },
    ),
    Achievement(
        name="друзья навеки",
        emoji="🫂",
        desc="пригласи друга по твоей реферальной ссылке и раздели веселье вместе с другом",
        need=1,
        reward={
            "буст": 2,
        },
    ),
]
