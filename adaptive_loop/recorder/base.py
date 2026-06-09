import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, List


class Outcome(Enum):
    SUCCESS = "success"
    FALLBACK = "fallback"
    ERROR = "error"


@dataclass
class AdaptEvent:
    timestamp: float
    template_name: str
    problem: str
    outcome: Outcome
    value: Any
    latency: float


class NullRecorder:
    """Recorder that discards all events."""

    async def record(self, event: AdaptEvent):
        pass


class InMemoryRecorder:
    """In-memory recorder for auditing and debugging."""

    def __init__(self):
        self._events: List[AdaptEvent] = []

    async def record(self, event: AdaptEvent):
        self._events.append(event)

    def get_all(self) -> List[AdaptEvent]:
        return list(self._events)

    def get_by_outcome(self, outcome: Outcome) -> List[AdaptEvent]:
        return [e for e in self._events if e.outcome == outcome]

    def get_by_template(self, template_name: str) -> List[AdaptEvent]:
        return [e for e in self._events if e.template_name == template_name]

    def clear(self):
        self._events.clear()
