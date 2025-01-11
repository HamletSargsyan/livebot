import asyncio
from typing import Any, Awaitable, Final, ParamSpec, TypedDict, TypeVar

from config import logger

T = TypeVar("T")
P = ParamSpec("P")


class TaskManagerTaskConfig(TypedDict):
    repeat_time: float
    delay: float


DEFAULT_TASK_MANAGER_CONFIG: TaskManagerTaskConfig = {
    "repeat_time": 0.0,
    "delay": 0.0,
}


class TaskManager:
    def __init__(self):
        self.loop = asyncio.get_event_loop()
        self.tasks: list[asyncio.Task] = []

    def add_task(
        self,
        func: Awaitable[Any],
        _config: TaskManagerTaskConfig = DEFAULT_TASK_MANAGER_CONFIG,
        *args,
        **kwargs,
    ) -> None:
        """Добавляет задачу в список для выполнения."""
        if any(task.get_coro().__name__ == func.__name__ for task in self.tasks):
            raise RuntimeError(f"Coroutine {func.__name__} is already added.")

        print(f"Добавление задачи {func.__name__}")
        task = self.loop.create_task(self._task_executor(func, _config=_config))
        self.tasks.append(task)

    async def run(self):
        """Запускает выполнение всех добавленных задач."""
        # try:
        #     self.loop.run_until_complete(asyncio.gather(*self.tasks))
        # finally:
        #     self.loop.close()
        await asyncio.gather(*self.tasks)

    async def _task_executor(self, coro: Awaitable[Any], _config: TaskManagerTaskConfig) -> None:
        """Выполняет задачу с заданной задержкой и/или интервалом."""
        _config = _config | DEFAULT_TASK_MANAGER_CONFIG

        await asyncio.sleep(_config["delay"])

        while True:
            try:
                await coro
            except Exception as e:
                logger.error(f"Error occurred in {coro.__name__}: {e}")

            if not _config["repeat_time"]:
                break

            await asyncio.sleep(_config["repeat_time"])


task_manager: Final = TaskManager()
