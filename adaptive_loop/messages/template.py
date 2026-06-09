from typing import Any, Dict, List, Optional


class PromptTemplate:
    def __init__(
        self,
        name: str,
        user: str,
        system: Optional[str] = None,
        parser_chain: Optional[List[str]] = None,
    ):
        self.name = name
        self.system = system
        self.user = user
        self.parser_chain = parser_chain or []

    def render(
        self,
        values: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> str:
        merged = dict(values or {})
        merged.update(kwargs)
        try:
            return self.user.format(**merged)
        except KeyError as e:
            raise ValueError(f"Missing template variable: {e}") from e
