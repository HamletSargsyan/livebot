from telebot.apihelper import ApiTelegramException
from telebot.util import antiflood, quick_markup

from database.funcs import database
from database.models import NotificationModel
from helpers.exceptions import NoResult
from config import bot
from helpers.utils import utcnow


def notification():
    while True:
        try:
            users = database.users.get_all()

            for user in users:
                try:
                    user_notification = database.notifications.get(owner=user._id)
                except NoResult:
                    user_notification = NotificationModel(owner=user._id)
                    id = database.notifications.add(**user_notification.to_dict()).inserted_id
                    user_notification._id = id

                user = database.users.get(_id=user._id)
                if not user.action:
                    continue
                try:
                    current_time = utcnow()
                    if user.action.end <= current_time:
                        if user.action.type == "street" and not user_notification.walk:
                            user_notification.walk = True
                            mess = "Ты закончил прогулку"
                        elif user.action.type == "work" and not user_notification.work:
                            user_notification.work = True
                            mess = "Ты закончил работу"
                        elif user.action.type == "sleep" and not user_notification.sleep:
                            user_notification.sleep = True
                            mess = "Ты проснулся"
                        elif user.action.type == "game" and not user_notification.game:
                            user_notification.game = True
                            mess = "Ты проснулся"
                        else:
                            continue

                        markup = quick_markup({"Дом": {"callback_data": f"open home {user.id}"}})
                        antiflood(bot.send_message, user.id, mess, reply_markup=markup)

                except ApiTelegramException:
                    continue

                database.notifications.update(**user_notification.to_dict())
        except Exception:
            continue
