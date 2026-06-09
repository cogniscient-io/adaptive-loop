import asyncio
import hashlib
import time
from typing import Any, Dict, Optional

from adaptive_loop.adapter.litellm import LiteLLMAdapter, AdaptRequest, AdaptResponse
from adaptive_loop.cache.base import LRUCache, NullCache
from adaptive_loop.messages.registry import PromptRegistry
from adaptive_loop.parser.chain import ParserChain
from adaptive_loop.recorder.base import InMemoryRecorder, NullRecorder, Outcome, AdaptEvent
from adaptive_loop.exceptions import AdapterError


class AdaptiveLoop:
    """Orchestrator: wires template, adapter, cache, parser, and recorder together."""

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        registry: Optional[PromptRegistry] = None,
        cache: Optional[LRUCache] = None,
        recorder: Optional[InMemoryRecorder] = None,
        timeout: float = 30.0,
    ):
        self._registry = registry or PromptRegistry()
        self._cache = cache or NullCache()
        self._recorder = recorder or NullRecorder()
        self._timeout = timeout

        self._adapter = LiteLLMAdapter(model=model)

    async def adapt(
        self,
        template: str,
        problem: str,
        data: Any = None,
        error: Optional[str] = None,
        fallback: Any = None,
        **extra: Any,
    ) -> Any:
        tpl = self._registry.get(template)
        rendered = tpl.render(problem=problem, data=data, error=error, **extra)

        key = self._cache_key(template, str(data), problem)
        cached = await self._cache.get(key)
        if cached is not None:
            await self._recorder.record(AdaptEvent(
                timestamp=time.monotonic(),
                template_name=template,
                problem=problem,
                outcome=Outcome.SUCCESS,
                value=cached,
                latency=0,
            ))
            return cached

        start = time.monotonic()
        try:
            system = tpl.system
            request = AdaptRequest(user_message=rendered, system_message=system)
            response = await self._adapter.send(request, timeout=self._timeout)

            chain = ParserChain(tpl.parser_chain or ["key_value", "numeric"])
            parsed = chain.parse(response.raw)

            if parsed.is_success:
                await self._cache.set(key, parsed.value)
                latency = time.monotonic() - start
                await self._recorder.record(AdaptEvent(
                    timestamp=start,
                    template_name=template,
                    problem=problem,
                    outcome=Outcome.SUCCESS,
                    value=parsed.value,
                    latency=latency,
                ))
                return parsed.value

            latency = time.monotonic() - start
            await self._recorder.record(AdaptEvent(
                timestamp=start,
                template_name=template,
                problem=problem,
                outcome=Outcome.FALLBACK,
                value=fallback,
                latency=latency,
            ))
            return fallback

        except Exception:
            latency = time.monotonic() - start
            await self._recorder.record(AdaptEvent(
                timestamp=start,
                template_name=template,
                problem=problem,
                outcome=Outcome.ERROR,
                value=fallback,
                latency=latency,
            ))
            return fallback

    def adapt_sync(
        self,
        template: str,
        problem: str,
        data: Any = None,
        error: Optional[str] = None,
        fallback: Any = None,
        **extra: Any,
    ) -> Any:
        """Sync wrapper using asyncio.run()."""
        return asyncio.run(self.adapt(
            template=template,
            problem=problem,
            data=data,
            error=error,
            fallback=fallback,
            **extra,
        ))

    def _cache_key(self, template: str, context: str, problem: str) -> str:
        raw = f"{template}|{context}|{problem}"
        return hashlib.sha256(raw.encode()).hexdigest()
