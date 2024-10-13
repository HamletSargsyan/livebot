from typing import Dict, List, Tuple, Union

import transliterate
from helpers.enums import ItemRarity, WeatherType

# ---------------------------------- Weather --------------------------------- #

weather_types = {
    "1": WeatherType.THUNDERSTORM,
    "3": WeatherType.DRIZZLE,
    "5": WeatherType.RAIN,
    "6": WeatherType.SNOW,
    "7": WeatherType.FOG,
    "800": WeatherType.CLEAR,
    "80": WeatherType.CLOUDS,
}

weather_emojis = {
    "Clear": "☀️",
    "Clouds": "☁️",
    "Drizzle": "🌦️",
    "Rain": "🌧️",
    "Thunderstorm": "⛈️",
    "Snow": "❄️",
    "Mist": "🌫️",
    "Smoke": "🌫️",
    "Haze": "🌫️",
    "Dust": "🌫️",
    "Fog": "🌫️",
    "Sand": "🌫️",
    "Ash": "🌫️",
    "Squall": "🌫️",
    "Tornado": "🌪️",
}


class Coordinates:
    def __init__(self, coord_data: dict):
        self.lon: float = coord_data.get("lon", 0.0)
        self.lat: float = coord_data.get("lat", 0.0)


class Weather:
    def __init__(self, weather_data: dict):
        self.id: int = weather_data.get("id", 0)
        self.main: str = weather_data.get("main", "")
        self.description: str = weather_data.get("description", "")
        self.icon: str = weather_data.get("icon", "")

    @property
    def ru_name(self):
        for _id, _weather_type in weather_types.items():
            if str(self.id).startswith(_id):
                return _weather_type.value
        return ""

    @property
    def emoji(self):
        return weather_emojis.get(str(self.main), "❓")


class MainInfo:
    def __init__(self, main_data: dict):
        self.temp: float = main_data.get("temp", 0.0)
        self.feels_like: float = main_data.get("feels_like", 0.0)
        self.temp_min: float = main_data.get("temp_min", 0.0)
        self.temp_max: float = main_data.get("temp_max", 0.0)
        self.pressure: int = main_data.get("pressure", 0)
        self.humidity: int = main_data.get("humidity", 0)


class WindInfo:
    def __init__(self, wind_data: dict):
        self.speed: float = wind_data.get("speed", 0.0)
        self.deg: float = wind_data.get("deg", 0.0)


class CloudsInfo:
    def __init__(self, clouds_data: dict):
        self.all: int = clouds_data.get("all", 0)


class SysInfo:
    def __init__(self, sys_data: dict):
        self.type: int = sys_data.get("type", 0)
        self.id: int = sys_data.get("id", 0)
        self.country: str = sys_data.get("country", "")
        self.sunrise: int = sys_data.get("sunrise", 0)
        self.sunset: int = sys_data.get("sunset", 0)


class WeatherData:
    def __init__(self, data: dict):
        self.data: dict = data
        self.coord: Coordinates = Coordinates(data.get("coord", {}))
        self.weather: Weather = Weather(data.get("weather", [{}])[0])
        self.base: str = data.get("base", "")
        self.main: MainInfo = MainInfo(data.get("main", {}))
        self.visibility: int = data.get("visibility", 0)
        self.wind: WindInfo = WindInfo(data.get("wind", {}))
        self.clouds: CloudsInfo = CloudsInfo(data.get("clouds", {}))
        self.dt: int = data.get("dt", 0)
        self.sys: SysInfo = SysInfo(data.get("sys", {}))
        self.timezone: int = data.get("timezone", 0)
        self.id: int = data.get("id", 0)
        self.name: str = data.get("name", "")
        self.cod: int = data.get("cod", 0)


# ----------------------------------- Item ----------------------------------- #


class Item:
    def __init__(
        self,
        /,
        name: str,
        emoji: str,
        desc: str,
        rarity: ItemRarity,
        is_task_item: bool = False,
        can_exchange: bool = False,
        is_usable: bool = False,
        altnames: Union[List[str], None] = None,
        craft: Union[Dict[str, int], None] = None,
        effect: Union[int, None] = None,
        price: Union[int, None] = None,
        task_coin: Union[Tuple[int, int], None] = None,
        exchange_price: Union[Tuple[int, int], None] = None,
        strength: Union[float, None] = None,
        strength_reduction: Union[tuple[float, float], None] = None,
        can_equip: bool = False,
    ):
        self.name = name
        self.emoji = emoji
        self.desc = desc
        self.craft = craft
        self.effect = effect
        self.price = price
        self.is_usable = is_usable
        self.altnames = altnames
        self.rarity = rarity
        self.is_task_item = is_task_item
        self.task_coin = task_coin
        self.can_exchange = can_exchange
        self.exchange_price = exchange_price
        self.strength = strength
        self.strength_reduction = strength_reduction
        self.can_equip = can_equip

    def __repr__(self) -> str:
        return f"<Item {self.name}>"

    def __str__(self) -> str:
        return self.__repr__()

    def translit(self):
        return transliterate.translit(self.name, reversed=True)
