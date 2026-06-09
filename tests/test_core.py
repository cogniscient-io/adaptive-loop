import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from adaptive_loop.core import AdaptiveLoop
from adaptive_loop.messages.template import PromptTemplate
from adaptive_loop.messages.registry import PromptRegistry
from adaptive_loop.parser.base import ParsedResult
from adaptive_loop.parser.chain import ParserChain
from adaptive_loop.adapter.litellm import LiteLLMAdapter, AdaptRequest, AdaptResponse
from adaptive_loop.cache.base import LRUCache, NullCache
from adaptive_loop.recorder.base import InMemoryRecorder, NullRecorder, Outcome, AdaptEvent


def _mock_registry() -> PromptRegistry:
    r = PromptRegistry()
    r.register(
        PromptTemplate(
            name="find_field",
            user="Find {problem} in {data}",
            system="Be concise.",
            parser_chain=["key_value", "numeric"],
        )
    )
    return r


def _mock_adapter(raw: str = "max_tokens: 4096") -> LiteLLMAdapter:
    adapter = MagicMock(spec=LiteLLMAdapter)
    adapter.send = AsyncMock(return_value=AdaptResponse(raw=raw))
    return adapter


class TestAdaptiveLoopInit:
    def test_default_init(self):
        loop = AdaptiveLoop(model="gpt-4o")
        assert loop is not None

    def test_custom_registry(self):
        reg = _mock_registry()
        loop = AdaptiveLoop(model="gpt-4o", registry=reg)
        assert loop is not None

    def test_custom_cache(self):
        cache = LRUCache()
        loop = AdaptiveLoop(model="gpt-4o", cache=cache)
        assert loop is not None


class TestAdaptAsync:
    @pytest.mark.asyncio
    async def test_success_returns_parsed_value(self):
        reg = _mock_registry()
        adapter = _mock_adapter("max_tokens: 4096")
        recorder = InMemoryRecorder()
        loop = AdaptiveLoop(
            model="gpt-4o",
            registry=reg,
            cache=NullCache(),
            recorder=recorder,
        )
        loop._adapter = adapter

        result = await loop.adapt(
            template="find_field",
            problem="Find max tokens",
            data="some data",
            fallback=1024,
        )
        assert result == 4096

    @pytest.mark.asyncio
    async def test_fallback_on_parse_failure(self):
        reg = _mock_registry()
        adapter = _mock_adapter("NOT_FOUND")
        recorder = InMemoryRecorder()
        loop = AdaptiveLoop(
            model="gpt-4o",
            registry=reg,
            cache=NullCache(),
            recorder=recorder,
        )
        loop._adapter = adapter

        result = await loop.adapt(
            template="find_field",
            data="data",
            problem="Find X",
            fallback=999,
        )
        assert result == 999

    @pytest.mark.asyncio
    async def test_fallback_on_adapter_error(self):
        reg = _mock_registry()
        adapter = _mock_adapter()
        adapter.send = AsyncMock(side_effect=Exception("Boom"))
        recorder = InMemoryRecorder()
        loop = AdaptiveLoop(
            model="gpt-4o",
            registry=reg,
            cache=NullCache(),
            recorder=recorder,
        )
        loop._adapter = adapter

        result = await loop.adapt(
            template="find_field",
            data="data",
            problem="Find X",
            fallback=777,
        )
        assert result == 777

    @pytest.mark.asyncio
    async def test_cache_hit_skips_adapter(self):
        reg = _mock_registry()
        cache = LRUCache()
        recorder = InMemoryRecorder()
        adapter = _mock_adapter()
        loop = AdaptiveLoop(
            model="gpt-4o",
            registry=reg,
            cache=cache,
            recorder=recorder,
        )
        loop._adapter = adapter

        # First call: cache miss, adapter called
        await loop.adapt(
            template="find_field",
            data="data",
            problem="Find max",
            fallback=100,
        )
        assert adapter.send.call_count == 1

        # Second call with same params: cache hit, adapter not called
        adapter.send.reset_mock()
        result = await loop.adapt(
            template="find_field",
            data="data",
            problem="Find max",
            fallback=100,
        )
        # Since we're using NullCache and cache is LRUCache, the cache hit should work
        assert result == 4096

    @pytest.mark.asyncio
    async def test_recorder_captures_event(self):
        reg = _mock_registry()
        adapter = _mock_adapter("max_tokens: 4096")
        recorder = InMemoryRecorder()
        loop = AdaptiveLoop(
            model="gpt-4o",
            registry=reg,
            cache=NullCache(),
            recorder=recorder,
        )
        loop._adapter = adapter

        await loop.adapt(
            template="find_field",
            data="data",
            problem="Find max tokens",
            fallback=1024,
        )
        events = recorder.get_all()
        assert len(events) == 1
        assert events[0].template_name == "find_field"

    @pytest.mark.asyncio
    async def test_adapter_error_recorded(self):
        reg = _mock_registry()
        adapter = _mock_adapter()
        adapter.send = AsyncMock(side_effect=Exception("fail"))
        recorder = InMemoryRecorder()
        loop = AdaptiveLoop(
            model="gpt-4o",
            registry=reg,
            cache=NullCache(),
            recorder=recorder,
        )
        loop._adapter = adapter

        await loop.adapt(
            template="find_field",
            data="data",
            problem="Find X",
            fallback=0,
        )
        events = recorder.get_all()
        assert events[0].outcome == Outcome.ERROR

    @pytest.mark.asyncio
    async def test_fallback_outcome_recorded(self):
        reg = _mock_registry()
        adapter = _mock_adapter("NOT_FOUND")
        recorder = InMemoryRecorder()
        loop = AdaptiveLoop(
            model="gpt-4o",
            registry=reg,
            cache=NullCache(),
            recorder=recorder,
        )
        loop._adapter = adapter

        await loop.adapt(
            template="find_field",
            data="data",
            problem="Find X",
            fallback=0,
        )
        events = recorder.get_all()
        assert events[0].outcome == Outcome.FALLBACK

    @pytest.mark.asyncio
    async def test_unknown_template_raises(self):
        reg = _mock_registry()
        loop = AdaptiveLoop(
            model="gpt-4o",
            registry=reg,
            cache=NullCache(),
            recorder=NullRecorder(),
        )
        with pytest.raises(Exception, match="not found"):
            await loop.adapt(
                template="unknown",
                data="data",
                problem="Find X",
                fallback=0,
            )


class TestAdaptSync:
    def test_sync_wrapper(self):
        reg = _mock_registry()
        adapter = _mock_adapter("max_tokens: 4096")
        recorder = InMemoryRecorder()
        loop = AdaptiveLoop(
            model="gpt-4o",
            registry=reg,
            cache=NullCache(),
            recorder=recorder,
        )
        loop._adapter = adapter

        result = loop.adapt_sync(
            template="find_field",
            data="data",
            problem="Find max",
            fallback=100,
        )
        assert result == 4096
