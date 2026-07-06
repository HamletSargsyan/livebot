import hashlib
import pickle
import time
from functools import wraps
from inspect import iscoroutinefunction
from pathlib import Path
from typing import Any, Awaitable, Callable, Literal, Optional, ParamSpec, TypeVar

from cachetools import LRUCache

from livebot.consts import CACHE_DIR, VERSION


P = ParamSpec("P")
T = TypeVar("T")


def make_hash(*args: Any) -> str:
    def convert(obj: Any) -> Any:
        if hasattr(obj, "to_dict"):
            return obj.to_dict()
        if isinstance(obj, dict):
            return {k: convert(v) for k, v in obj.items()}
        if isinstance(obj, (list, set, tuple)):
            return type(obj)(convert(v) for v in obj)
        return obj

    converted_args = tuple(convert(arg) for arg in args)
    key = pickle.dumps(converted_args)
    return hashlib.md5(key).hexdigest()


class DiskCache:
    def __init__(self, path: Path, max_items: int = 2048):
        self.path = path / f"{VERSION.major}.{VERSION.minor}"
        self.path.mkdir(exist_ok=True)
        self.index_file = self.path / "index.pkl"
        self.index = self._load_index()
        self.max_items = max_items

    def _load_index(self) -> dict[str, float]:
        if self.index_file.exists():
            with open(self.index_file, "rb") as f:
                return pickle.load(f)
        return {}

    def _save_index(self) -> None:
        with open(self.index_file, "wb") as f:
            pickle.dump(self.index, f)

    def _item_path(self, key: str) -> Path:
        return self.path / f"{key}.pkl"

    def get(self, key: str, expire: Optional[int]) -> Optional[Any]:
        if key not in self.index:
            return None
        now = time.time()
        if expire is not None and now - self.index[key] > expire:
            self.delete(key)
            return None
        item_path = self._item_path(key)
        if not item_path.exists():
            return None
        with open(item_path, "rb") as f:
            return pickle.load(f)

    def set(self, key: str, value: Any) -> None:
        if len(self.index) >= self.max_items:
            oldest_key = min(self.index.items(), key=lambda x: x[1])[0]
            self.delete(oldest_key)
        item_path = self._item_path(key)
        with open(item_path, "wb") as f:
            pickle.dump(value, f)
        self.index[key] = time.time()
        self._save_index()

    def delete(self, key: str) -> None:
        self.index.pop(key, None)
        path = self._item_path(key)
        if path.exists():
            path.unlink()
        self._save_index()


ram_cache: LRUCache[str, tuple[Any, float]] = LRUCache(4048 * 2)
disk_cache = DiskCache(CACHE_DIR)


async def _async_wrapper(
    func: Callable[P, Awaitable[T]],
    key: str,
    expire: Optional[int],
    storage: Literal["ram", "disk"],
    *args: P.args,
    **kwargs: P.kwargs,
) -> T:
    now = time.time()

    if storage == "ram":
        if key in ram_cache:
            val, timestamp = ram_cache[key]
            if expire is None or now - timestamp < expire:
                return val
    elif storage == "disk":
        cached = disk_cache.get(key, expire)
        if cached is not None:
            return cached

    result = await func(*args, **kwargs)
    if storage == "ram":
        ram_cache[key] = (result, now)
    elif storage == "disk":
        disk_cache.set(key, result)
    return result


def _sync_wrapper(
    func: Callable[P, T],
    key: str,
    expire: Optional[int],
    storage: Literal["ram", "disk"],
    *args: P.args,
    **kwargs: P.kwargs,
) -> T:
    now = time.time()

    if storage == "ram":
        if key in ram_cache:
            val, timestamp = ram_cache[key]
            if expire is None or now - timestamp < expire:
                return val
    elif storage == "disk":
        cached = disk_cache.get(key, expire)
        if cached is not None:
            return cached

    result = func(*args, **kwargs)
    if storage == "ram":
        ram_cache[key] = (result, now)
    elif storage == "disk":
        disk_cache.set(key, result)
    return result


def cached(
    *,
    expire: Optional[int] = None,
    storage: Literal["ram", "disk"] = "ram",
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        if iscoroutinefunction(func):

            @wraps(func)
            async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
                key = make_hash(func.__name__, *args, kwargs)
                return await _async_wrapper(func, key, expire, storage, *args, **kwargs)

            return async_wrapper  # type: ignore

        @wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            key = make_hash(func.__name__, *args, kwargs)
            return _sync_wrapper(func, key, expire, storage, *args, **kwargs)

        return sync_wrapper

    return decorator
