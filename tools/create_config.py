import os
import toml

config = {
    "general": {
        "debug": False,
    },
    "database": {
        "url": "your_db_url",
        "name": "livebot",
    },
    "redis": {
        "url": "your_redis_url",
    },
    "telegram": {
        "token": "your_bot_token",
        "log_chat_id": "",
        "log_thread_id": 2,
        "owners": [5161392463],
    },
    "weather": {
        "api_key": "your_openweather_api_key",
        "region": "",
    },
    "event": {
        "start_time": "",
        "end_time": "",
        "open": False,
    },
    "channel": {
        "id": "",
        "chat_id": "",
    },
}


if os.path.exists("config.toml"):
    print("Конфигурационный файл существует")
    exit(1)

with open("config.toml", "w") as f:
    toml.dump(config, f)

print("Конфигурационный файл успешно создан.")
