import pytest

from adaptive_loop.exceptions import (
    AdapterError,
    AdaptiveLoopError,
    ParseError,
    TemplateError,
)


def test_exception_hierarchy():
    assert issubclass(ParseError, AdaptiveLoopError)
    assert issubclass(AdapterError, AdaptiveLoopError)
    assert issubclass(TemplateError, AdaptiveLoopError)


def test_raise_and_catch():
    with pytest.raises(AdaptiveLoopError):
        raise ParseError("bad parse")

    with pytest.raises(AdaptiveLoopError):
        raise AdapterError("bad adapter")

    with pytest.raises(AdaptiveLoopError):
        raise TemplateError("bad template")
