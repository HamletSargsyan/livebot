from datetime import datetime
import venv
import tempfile
import subprocess
from pathlib import Path

import rich.status


def log(message: str):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")


def run(*args):
    return subprocess.run(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


# log("Настройка установщика... (может занять пару минут)")
# INSTALLER_VENV_PATH = Path(tempfile.mkdtemp())

# venv.create(INSTALLER_VENV_PATH, with_pip=True)

# pip = INSTALLER_VENV_PATH / "bin" / "pip"

# run(
#     pip,
#     "install",
#     "--disable-pip-version-check",
#     "questionary",
#     "rich",
#     "httpx",
#     "semver",
# )
# log("Настройка завершена")


import httpx  # noqa: #402
import rich  # noqa: E402
from rich.console import Console  # noqa: E402
import questionary  # noqa: E402
import questionary.prompt  # noqa: E402

console = Console()

available_version: list[str] = []

with console.status("Получение версий"):
    response = httpx.get("https://api.github.com/repos/HamletSargsyan/livebot/releases")
    print(response.url)
    if response.status_code == 200:
        releases = response.json()
        for release in releases:
            print(release)
            available_version.append(release["tag_name"])
    else:
        print(
            f"Failed to fetch releases. Status code: {response.status_code} | Text: {response.text}"
        )

print(available_version)
answers = questionary.form(
    version=questionary.select("Выберете версию", choices=available_version)
).ask()

print(answers)
