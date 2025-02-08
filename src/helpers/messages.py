from database.models import UserModel


class Messages:
    @classmethod
    def profile(cls, user: UserModel) -> str:
        return (
            f"<b>Профиль {user.name}</b>\n\n"
            f"❤️ Здоровье: {user.health}\n"
            f"🎭 Настроение: {user.mood}\n"
            f"💤 Усталость: {user.fatigue}\n"
            f"🍞 Голод: {user.hunger}\n"
            f"🪙 Бабло: {user.coin}\n"
            f"🍀 Удача: {user.luck}\n"
            f"🏵 Уровень: {user.level}\n"
            f"⚡ Карма: {user.karma}\n"
            f"🎗 Опыт {int(user.xp)}/{int(user.max_xp)}\n"
        )
