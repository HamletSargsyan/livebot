import asyncio
import random
from itertools import filterfalse

from base.player import check_user_stats
from database.funcs import database
from helpers.utils import utcnow


async def _check():
    users = await database.users.async_get_all()

    for user in users:
        user = await database.users.async_get(_id=user._id)
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

        await database.users.async_update(**user.to_dict())
        await check_user_stats(user)


async def check():
    while True:
        await _check()
        await asyncio.sleep(3600)  # 1h
