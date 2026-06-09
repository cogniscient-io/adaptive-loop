import pytest

from adaptive_loop.parser.chain import ParserChain
from adaptive_loop.parser.base import ParsedResult


class TestParserChain:
    def test_first_parser_wins_exact(self):
        chain = ParserChain(["key_value"])
        r = chain.parse("max_tokens: 4096")
        assert r.is_success
        assert r.value == 4096
        assert r.confidence == "exact"

    def test_fallback_to_second_parser(self):
        chain = ParserChain(["key_value", "numeric"])
        r = chain.parse("The value is 8192, not much else to say.")
        assert r.is_success
        assert r.value == 8192
        assert r.confidence == "fallback"

    def test_all_parsers_fail(self):
        chain = ParserChain(["key_value", "numeric"])
        r = chain.parse("NOT_FOUND")
        assert r.not_found
        assert r.confidence == "none"

    def test_empty_chain(self):
        chain = ParserChain([])
        r = chain.parse("some text")
        assert r.not_found

    def test_json_in_chain(self):
        chain = ParserChain(["json", "key_value"])
        r = chain.parse('{"max_tokens": 4096}')
        assert r.is_success
        assert r.value == 4096
        assert r.confidence == "exact"

    def test_fallback_json_to_numeric(self):
        chain = ParserChain(["json", "numeric"])
        r = chain.parse("Just the number 42 here")
        assert r.is_success
        assert r.value == 42
        assert r.confidence == "fallback"
