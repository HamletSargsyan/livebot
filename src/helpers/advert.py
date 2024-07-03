import asyncio
from typing import Union

from telebot.types import Message

from config import GRAMADS_TOKEN, logger
from database.models import UserModel


import aiohttp


async def show_advert(user_id: int):
    """
    Undefined = 0,
    Success = 1,
    RevokedTokenError = 2,
    UserForbiddenError = 3,
    ToManyRequestsError = 4,
    OtherBotApiError = 5,
    OtherError = 6,

    AdLimited = 7,
    NoAds = 8,
    BotIsNotEnabled=9,
    Banned=10,
    InReview=11
    """
    logger.info(f"Send advert to user `{user_id}`")
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://api.gramads.net/ad/SendPost",
            headers={
                "Authorization": f"Bearer {GRAMADS_TOKEN}",
                "Content-Type": "application/json",
            },
            json={"SendToChatId": user_id},
        ) as response:
            response.content
            if response.ok:
                logger.info(f"Advert for user `{user_id}` send successful")
            else:
                try:
                    logger.error("Gramads: %s" % str(await response.json()))
                except Exception:
                    logger.error("Gramads: %s" % str(await response.text()))


# def show_advert(user: UserModel):
#     headers = {
#         "Authorization": f"Bearer {GRAMADS_TOKEN}",
#         "Content-Type": "application/json",
#     }
#     json = {"SendToChatId": user.id}

#     response = requests.post(
#         "https://api.gramads.net/ad/SendPost", headers=headers, json=json
#     )

#     logger.debug(response.text)

#     if response.status_code == 200 and response.json()["SendPostResult"] == 1:
#         user.last_advert_time = datetime.utcnow()
#         user.adverts_count += 1
#         database.users.update(**user.to_dict())
#     else:
#         try:
#             logger.error(response.json())
#         except Exception:
#             logger.error(response.text)


def send_advert(message: Message, user: Union[UserModel, None] = None):
    if message.chat.type != "private":
        return

    # if not user:
    #     user = database.users.get(id=message.from_user.id)

    asyncio.run(show_advert(message.from_user.id))
