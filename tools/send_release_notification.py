import os
import requests

from telebot import TeleBot
from telebot.util import quick_markup

def get_github_release_info(version):
    url = f"  https://api.github.com/repos/HamletSargsyan/livebot/releases/tags/{version}"
    response = requests.get(url)
    if response.status_code == 200:
        release_info = response.json() #type: dict
        return release_info
    response.raise_for_status()
    

def send_release_notification():
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("CHAT_ID")
    
    release_version = os.getenv("GITHUB_REF").split("/")[-1]
    release = get_github_release_info(release_version) # type: dict
        
    message = (f"*{'Пре-р' if release.get('prerelease') else 'р'}елиз — {release.get('name')}* ✨\n\n"
               f"{release.get('body')}")
    
    markup = quick_markup({
        "Релиз": {"url": release.get("html_url")}
    })
    
    bot = TeleBot(bot_token, parse_mode="markdown")
    bot.send_message(chat_id, message, reply_markup=markup)

if __name__ == "__main__":
    send_release_notification()
