import time
from collections import OrderedDict
from typing import Any, Optional


class NullCache:
    """Pass-through cache that never stores anything."""

    async def get(self, key: str) -> Optional[Any]:
        return None

    async def set(self, key: str, value: Any, ttl: int = 3600):
        pass


class LRUCache:
    """Simple in-memory LRU cache with TTL support."""

    def __init__(self, max_size: int = 128):
        self._max_size = max_size
        self._store: OrderedDict[str, Any] = OrderedDict()
        self._expiry: dict[str, float] = {}

    async def get(self, key: str) -> Optional[Any]:
        if key not in self._store:
            return None
        if self._expiry.get(key, 0) < time.monotonic():
            del self._store[key]
            del self._expiry[key]
            return None
        # Move to end (most recent)
        self._store.move_to_end(key)
        return self._store[key]

    async def set(self, key: str, value: Any, ttl: int = 3600):
        if key in self._store:
            self._store.move_to_end(key)
        self._store[key] = value
        self._expiry[key] = time.monotonic() + ttl
        # Evict oldest if over capacity
        while len(self._store) > self._max_size:
            oldest, _ = self._store.popitem(last=False)
            self._expiry.pop(oldest, None)
