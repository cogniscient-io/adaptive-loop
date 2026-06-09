from adaptive_loop.parser.base import ParsedResult


class TestParsedResult:
    def test_success(self):
        r = ParsedResult(value=42)
        assert r.is_success
        assert not r.not_found
        assert r.value == 42
        assert r.confidence == "exact"

    def test_not_found_via_confidence(self):
        r = ParsedResult(value=None, confidence="none")
        assert not r.is_success
        assert r.not_found

    def test_raw_property(self):
        r = ParsedResult(value="hello")
        assert r.raw == "hello"

    def test_raw_none_when_no_value(self):
        r = ParsedResult(value=None, confidence="none")
        assert r.raw is None
