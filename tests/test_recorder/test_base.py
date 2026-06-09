import time

import pytest

from adaptive_loop.recorder.base import (
    AdaptEvent,
    InMemoryRecorder,
    NullRecorder,
    Outcome,
)


def _event(**kwargs) -> AdaptEvent:
    defaults = dict(
        timestamp=time.monotonic(),
        template_name="test",
        problem="find field",
        outcome=Outcome.SUCCESS,
        value=42,
        latency=0.1,
    )
    defaults.update(kwargs)
    return AdaptEvent(**defaults)


class TestNullRecorder:
    @pytest.mark.asyncio
    async def test_record_does_nothing(self):
        r = NullRecorder()
        await r.record(_event())


class TestInMemoryRecorder:
    @pytest.mark.asyncio
    async def test_record_and_get_all(self):
        r = InMemoryRecorder()
        e = _event()
        await r.record(e)
        assert len(r.get_all()) == 1
        assert r.get_all()[0] is e

    @pytest.mark.asyncio
    async def test_get_by_outcome(self):
        r = InMemoryRecorder()
        await r.record(_event(outcome=Outcome.SUCCESS))
        await r.record(_event(outcome=Outcome.FALLBACK))
        assert len(r.get_by_outcome(Outcome.SUCCESS)) == 1
        assert len(r.get_by_outcome(Outcome.FALLBACK)) == 1
        assert len(r.get_by_outcome(Outcome.ERROR)) == 0

    @pytest.mark.asyncio
    async def test_get_by_template(self):
        r = InMemoryRecorder()
        await r.record(_event(template_name="tmpl1"))
        await r.record(_event(template_name="tmpl2"))
        assert len(r.get_by_template("tmpl1")) == 1
        assert len(r.get_by_template("tmpl2")) == 1

    @pytest.mark.asyncio
    async def test_clear(self):
        r = InMemoryRecorder()
        await r.record(_event())
        r.clear()
        assert len(r.get_all()) == 0
