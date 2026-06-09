import pytest

from adaptive_loop.cache.base import NullCache, LRUCache


class TestNullCache:
    @pytest.mark.asyncio
    async def test_get_returns_none(self):
        c = NullCache()
        assert await c.get("missing") is None

    @pytest.mark.asyncio
    async def test_set_does_nothing(self):
        c = NullCache()
        await c.set("key", "value")
        assert await c.get("key") is None


class TestLRUCache:
    @pytest.mark.asyncio
    async def test_set_and_get(self):
        c = LRUCache()
        await c.set("key", "value")
        assert await c.get("key") == "value"

    @pytest.mark.asyncio
    async def test_missing_key(self):
        c = LRUCache()
        assert await c.get("missing") is None

    @pytest.mark.asyncio
    async def test_overwrite(self):
        c = LRUCache()
        await c.set("key", "v1")
        await c.set("key", "v2")
        assert await c.get("key") == "v2"

    @pytest.mark.asyncio
    async def test_max_size_evicts(self):
        c = LRUCache(max_size=3)
        await c.set("a", 1)
        await c.set("b", 2)
        await c.set("c", 3)
        await c.set("d", 4)
        assert await c.get("a") is None  # evicted
        assert await c.get("d") == 4

    @pytest.mark.asyncio
    async def test_access_order(self):
        c = LRUCache(max_size=3)
        await c.set("a", 1)
        await c.set("b", 2)
        await c.set("c", 3)
        await c.get("a")  # access 'a' to make it most recent
        await c.set("d", 4)  # should evict 'b'
        assert await c.get("a") == 1
        assert await c.get("b") is None
        assert await c.get("d") == 4
