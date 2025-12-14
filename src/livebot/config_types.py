from argparse import Namespace
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import tomlkit
from mashumaro.mixins.toml import DataClassTOMLMixin

from livebot.consts import VERSION


@dataclass(kw_only=True)
class GeneralConfig:
    weather_region: str
    debug: bool = False
    owners: list[int] = field(default_factory=list)


@dataclass(kw_only=True)
class DatabaseConfig:
    url: str
    name: str = "livebot"


@dataclass(kw_only=True)
class RedisConfig:
    url: str


@dataclass(kw_only=True)
class TelegramConfig:
    token: str
    log_chat_id: int | str
    channel_id: int
    log_thread_id: Optional[int] = None


@dataclass(kw_only=True)
class Config(DataClassTOMLMixin):
    general: GeneralConfig
    database: DatabaseConfig
    redis: RedisConfig
    telegram: TelegramConfig

    def __post_serialize__(self, d: dict[Any, Any]) -> dict[Any, Any]:
        def remove_none_values(data: dict[Any, Any]) -> dict[Any, Any]:
            return {
                k: (remove_none_values(v) if isinstance(v, dict) else v)
                for k, v in data.items()
                if v is not None
            }

        return remove_none_values(d)

    @classmethod
    def from_file(cls, file: Path) -> "Config":
        if not file.exists():
            cls.create(file)
        with file.open("r", encoding="utf-8") as f:
            return cls.from_toml(f.read(), decoder=tomlkit.loads)

    @classmethod
    def create(cls, file: Path) -> bool:
        if file.exists():
            return False

        config = tomlkit.document()
        config.add(tomlkit.comment("config docs: https://0xM4LL0C.github.io/livebot/main/config/"))

        default_config = Config(
            general=GeneralConfig(weather_region="weather region"),
            database=DatabaseConfig(url="database_url"),
            redis=RedisConfig(url="redis_url"),
            telegram=TelegramConfig(
                token="bot token from @BotFather",
                log_chat_id="log chat id",
                channel_id=0,
            ),
        )

        config.update(default_config.to_dict())

        version = VERSION
        with file.open("w", encoding="utf-8") as f:
            f.write(
                f"#:schema https://raw.githubusercontent.com/0xM4LL0C/livebot/refs/tags/v{version}/config_schema.json\n\n"
            )
            f.write(tomlkit.dumps(config))

        return True

    def merge(self, args: Namespace) -> None:
        if args.debug:
            self.general.debug = args.debug
