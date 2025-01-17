import asyncio
import random
from itertools import filterfalse

from helpers.utils import utcnow
from database.funcs import database
from base.player import check_user_stats


async def _check():
    users = database.users.get_all()

    for user in users:
        user = database.users.get(_id=user._id)
        match random.randint(0, 5):
            case 0:
                user.hunger += 1
            case 1:
                user.fatigue += 1
            case 2:
                user.mood -= 1

        user.violations = list(
            filterfalse(
                lambda v: v.until_date and v.until_date < utcnow(),
                user.violations,
            )
        )

        database.users.update(**user.to_dict())
        await check_user_stats(user)


async def check():
    while True:
        await _check()
        await asyncio.sleep(3600)  # 1h
