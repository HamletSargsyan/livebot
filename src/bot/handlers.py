from telebot.types import Message

from config import bot


@bot.message_handler(commands=["start"])
def start_cmd(message: Message):
    bot.reply_to(message, f"Hello {message.from_user.full_name}")


# ---------------------------------------------------------------------------- #


@bot.message_handler(func=lambda m: True)
def message_handler(message: Message):
    bot.reply_to(message, message.text)
