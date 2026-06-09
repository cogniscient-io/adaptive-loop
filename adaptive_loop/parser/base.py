from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class ParsedResult:
    value: Any = None
    confidence: str = "exact"

    @property
    def is_success(self) -> bool:
        return self.confidence != "none"

    @property
    def not_found(self) -> bool:
        return not self.is_success

    @property
    def raw(self) -> Optional[str]:
        return str(self.value) if self.value is not None else None
