from typing import Union
import requests
from datetime import datetime, timedelta

from telebot.types import Message

from config import GRAMADS_TOKEN, logger
from database.models import UserModel
from database.funcs import database


def show_advert(user: UserModel):
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
    headers = {
        "Authorization": f"Bearer {GRAMADS_TOKEN}",
        "Content-Type": "application/json",
    }
    json = {"SendToChatId": user.id}

    response = requests.post(
        "https://api.gramads.net/ad/SendPost", headers=headers, json=json
    )

    logger.debug(f"Send advert to user `{user.id}`")

    if response.json()["SendPostResult"] == 1:
        user.last_advert_time = datetime.utcnow()
        user.adverts_count += 1
        database.users.update(**user.to_dict())
    else:
        logger.error(response.json())


def send_advert(message: Message, user: Union[UserModel, None] = None):
    if message.chat.type != "private":
        return

    if not user:
        user = database.users.get(id=message.from_user.id)

    if not user.last_advert_time:
        show_advert(user)
        return

    if user.last_advert_time > datetime.utcnow() + timedelta(minutes=5):
        show_advert(user)
