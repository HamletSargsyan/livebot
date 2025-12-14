from argparse import ArgumentParser, Namespace
from pathlib import Path
from typing import Final

from livebot.consts import CONFIG_FILE, VERSION


def parse_args() -> Namespace:
    parser = ArgumentParser()
    parser.add_argument("--debug", action="store_true", help="run in debug mode")
    parser.add_argument("--without-tasks", action="store_true", help="run without tasks")
    parser.add_argument("--no-interactive", action="store_true", help="disable prompts")
    parser.add_argument(
        "-v", "--version", action="version", version=str(VERSION), help="bot version"
    )
    parser.add_argument("-c", "--config", type=Path, default=CONFIG_FILE, help="config path")

    return parser.parse_args()


ARGS: Final[Namespace] = parse_args()
