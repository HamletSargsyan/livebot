import requests

from helpers.datatypes import WeatherData
from config import OPENWEATHER_API_KEY, weather_region
from helpers.utils import cached


@cached
def get_weather() -> WeatherData:
    url = "http://api.openweathermap.org/data/2.5/weather?"

    params = {
        "lang": "RU",
        "q": weather_region,
        "appid": OPENWEATHER_API_KEY,
        "units": "metric",
    }
    response = requests.get(url, params=params)
    return WeatherData(response.json())
