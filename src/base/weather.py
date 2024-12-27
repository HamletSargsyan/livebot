from typing import Any
import httpx

from database.funcs import cache
from helpers.datatypes import WeatherData
from config import config, logger


def _get_coords_from_region(name: str) -> tuple[float, float]:
    if f"coords_{name}" in cache:
        logger.debug("cache")
        return cache[f"coords_{name}"]

    url = "https://geocoding-api.open-meteo.com/v1/search"

    params = {
        "name": name,
        "count": 1,
    }
    response = httpx.get(url, params=params)
    data: dict[str, list[dict[str, Any]]] = response.json()

    result = data["results"][0]["latitude"], data["results"][0]["longitude"]
    cache[f"coords_{name}"] = result
    return result


def get_weather() -> WeatherData:
    if "weather_data" in cache:
        logger.debug("cache")
        return cache["weather_data"]
    logger.debug("new")

    coords = _get_coords_from_region(config.weather.region)
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": coords[0],
        "longitude": coords[1],
        "current": ["temperature_2m", "weather_code"],
        "hourly": ["temperature_2m", "weather_code"],
    }
    response = httpx.get(url, params=params)
    weather_data = WeatherData(response.json())

    cache["weather_data"] = weather_data

    return weather_data
