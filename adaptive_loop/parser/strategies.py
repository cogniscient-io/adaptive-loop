import json
import re
from typing import Optional

from adaptive_loop.parser.base import ParsedResult


class KeyValParser:
    """Extract FIELD: VALUE pattern from AI response text."""

    def parse(self, text: str) -> ParsedResult:
        text = text.strip()

        # Check for explicit NOT_FOUND
        if text.upper() == "NOT_FOUND":
            return ParsedResult(value=None, confidence="none")

        # Pattern: underscore-separated identifier at start of line, colon, value
        # This avoids matching natural language sentences with colons
        pattern = r'(?:^|\n)([\w]+):\s*(.+?)(?:\s*[,;\n]|$)'
        skip = {"field_name", "value", "field", "fieldname", "label"}
        for m in re.finditer(pattern, text, re.IGNORECASE):
            key = m.group(1).strip().lower()
            if key in skip or m.group(1).startswith("FIELD"):
                continue
            raw = m.group(2).strip().strip("'\"")
            value = _coerce(raw)
            return ParsedResult(value=value)

        # No pattern match, try numeric fallback
        return ParsedResult(value=None, confidence="none")


class NumericParser:
    """Extract the first numeric value from any text."""

    def parse(self, text: str) -> ParsedResult:
        text = text.strip()
        # Match optional negative sign and decimal
        m = re.search(r'-?\d+\.?\d*', text)
        if m:
            raw = m.group()
            value = _coerce(raw)
            return ParsedResult(value=value)
        return ParsedResult(value=None, confidence="none")


class JSONParser:
    """Parse JSON response and extract value."""

    def parse(self, text: str) -> ParsedResult:
        text = text.strip()
        # Strip markdown code fences if present
        if text.startswith("```"):
            lines = text.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            text = "\n".join(lines).strip()

        try:
            data = json.loads(text)
        except (json.JSONDecodeError, ValueError):
            return ParsedResult(value=None, confidence="none")

        if isinstance(data, dict):
            # Prefer 'value' key, then 'result'
            for key in ("value", "result", "max_tokens"):
                if key in data:
                    return ParsedResult(value=data[key])
            # Return first leaf value
            for v in data.values():
                if not isinstance(v, (dict, list)):
                    return ParsedResult(value=v)
            # If all values are nested, try first nested
            for v in data.values():
                if isinstance(v, dict):
                    for nv in v.values():
                        if not isinstance(nv, (dict, list)):
                            return ParsedResult(value=nv)
        elif isinstance(data, list) and data:
            return ParsedResult(value=data[0])

        return ParsedResult(value=None, confidence="none")


def _coerce(raw: str):
    """Try to convert string to int or float, else return stripped string."""
    try:
        return int(raw)
    except ValueError:
        pass
    try:
        return float(raw)
    except ValueError:
        pass
    return raw
