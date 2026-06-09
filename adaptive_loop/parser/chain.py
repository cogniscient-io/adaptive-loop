from typing import Dict, List, Optional, Type

from adaptive_loop.parser.base import ParsedResult
from adaptive_loop.parser.strategies import (
    JSONParser,
    KeyValParser,
    NumericParser,
)

_STRATEGIES: Dict[str, Type] = {
    "key_value": KeyValParser,
    "numeric": NumericParser,
    "json": JSONParser,
}


class ParserChain:
    """Run parsers in order until one succeeds."""

    def __init__(self, names: Optional[List[str]] = None):
        self._names = names or []

    def parse(self, text: str) -> ParsedResult:
        if not self._names:
            return ParsedResult(value=None, confidence="none")

        first = True
        for name in self._names:
            cls = _STRATEGIES.get(name)
            if cls is None:
                continue
            result = cls().parse(text)
            if result.is_success:
                result.confidence = "exact" if first else "fallback"
                return result
            first = False

        return ParsedResult(value=None, confidence="none")
