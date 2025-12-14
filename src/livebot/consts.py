from importlib.metadata import version
from typing import Final

from bson import ObjectId
from semver import Version
from xdg_base_dirs import xdg_cache_home, xdg_config_home, xdg_data_home


APP_NAME: Final = "livebot"

CONFIG_DIR: Final = xdg_config_home() / APP_NAME
CACHE_DIR: Final = xdg_cache_home() / APP_NAME
DATA_DIR: Final = xdg_data_home() / APP_NAME

CONFIG_FILE: Final = CONFIG_DIR / "config.toml"

COIN_EMOJI: Final = "🪙"
TELEGRAM_ID: Final = 777000
EMPTY_OBJECTID: Final = ObjectId("000000000000000000000000")

MINUTE: Final = 60
HOUR: Final = MINUTE * 60
DAY: Final = HOUR * 24
WEEK: Final = DAY * 7

VERSION: Final = Version.parse(version(APP_NAME))

AUTHOR = "0xM4LL0C"
REPO_URL: Final = f"https://github.com/{AUTHOR}/{APP_NAME}/"

MARKET_ITEMS_LIST_MAX_ITEMS_COUNT: Final = 5

SLOT_MACHINE_VALUE: Final = {
    1: ("bar", "bar", "bar"),
    2: ("grape", "bar", "bar"),
    3: ("lemon", "bar", "bar"),
    4: ("seven", "bar", "bar"),
    5: ("bar", "grape", "bar"),
    6: ("grape", "grape", "bar"),
    7: ("lemon", "grape", "bar"),
    8: ("seven", "grape", "bar"),
    9: ("bar", "lemon", "bar"),
    10: ("grape", "lemon", "bar"),
    11: ("lemon", "lemon", "bar"),
    12: ("seven", "lemon", "bar"),
    13: ("bar", "seven", "bar"),
    14: ("grape", "seven", "bar"),
    15: ("lemon", "seven", "bar"),
    16: ("seven", "seven", "bar"),
    17: ("bar", "bar", "grape"),
    18: ("grape", "bar", "grape"),
    19: ("lemon", "bar", "grape"),
    20: ("seven", "bar", "grape"),
    21: ("bar", "grape", "grape"),
    22: ("grape", "grape", "grape"),
    23: ("lemon", "grape", "grape"),
    24: ("seven", "grape", "grape"),
    25: ("bar", "lemon", "grape"),
    26: ("grape", "lemon", "grape"),
    27: ("lemon", "lemon", "grape"),
    28: ("seven", "lemon", "grape"),
    29: ("bar", "seven", "grape"),
    30: ("grape", "seven", "grape"),
    31: ("lemon", "seven", "grape"),
    32: ("seven", "seven", "grape"),
    33: ("bar", "bar", "lemon"),
    34: ("grape", "bar", "lemon"),
    35: ("lemon", "bar", "lemon"),
    36: ("seven", "bar", "lemon"),
    37: ("bar", "grape", "lemon"),
    38: ("grape", "grape", "lemon"),
    39: ("lemon", "grape", "lemon"),
    40: ("seven", "grape", "lemon"),
    41: ("bar", "lemon", "lemon"),
    42: ("grape", "lemon", "lemon"),
    43: ("lemon", "lemon", "lemon"),
    44: ("seven", "lemon", "lemon"),
    45: ("bar", "seven", "lemon"),
    46: ("grape", "seven", "lemon"),
    47: ("lemon", "seven", "lemon"),
    48: ("seven", "seven", "lemon"),
    49: ("bar", "bar", "seven"),
    50: ("grape", "bar", "seven"),
    51: ("lemon", "bar", "seven"),
    52: ("seven", "bar", "seven"),
    53: ("bar", "grape", "seven"),
    54: ("grape", "grape", "seven"),
    55: ("lemon", "grape", "seven"),
    56: ("seven", "grape", "seven"),
    57: ("bar", "lemon", "seven"),
    58: ("grape", "lemon", "seven"),
    59: ("lemon", "lemon", "seven"),
    60: ("seven", "lemon", "seven"),
    61: ("bar", "seven", "seven"),
    62: ("grape", "seven", "seven"),
    63: ("lemon", "seven", "seven"),
    64: ("seven", "seven", "seven"),
}
