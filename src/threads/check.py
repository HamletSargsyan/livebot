import random
import time

from database.funcs import database
from base.player import check_user_stats


def check():
    while True:
        try:
            users = database.users.get_all()

            for user in users:
                user = database.users.get(_id=user._id)
                choice = random.randint(0, 2)
                match choice:
                    case 0:
                        user.hunger += 1
                    case 1:
                        user.fatigue += 1
                    case 2:
                        user.mood -= 1

                database.users.update(**user.to_dict())
                check_user_stats(user)
            time.sleep(3600)  # 1h
        except Exception:
            continue
