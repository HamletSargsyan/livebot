import httpx

from cachetools import TTLCache

from helpers.datatypes import WeatherData
from config import config, logger


cache = TTLCache(maxsize=1, ttl=1800)


def get_weather() -> WeatherData:
    if "weather_data" in cache:
        logger.debug("cache")
        return cache["weather_data"]
    logger.debug("new")

    url = "http://api.openweathermap.org/data/2.5/weather?"
    params = {
        "lang": "RU",
        "q": config.weather.region,
        "appid": config.weather.api_key,
        "units": "metric",
    }
    response = httpx.get(url, params=params)
    weather_data = WeatherData(response.json())

    cache["weather_data"] = weather_data

    return weather_data
