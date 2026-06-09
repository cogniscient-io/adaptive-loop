import pytest

from adaptive_loop.parser.strategies import (
    KeyValParser,
    NumericParser,
    JSONParser,
)
from adaptive_loop.parser.base import ParsedResult


class TestKeyValParser:
    def test_simple_key_value(self):
        p = KeyValParser()
        r = p.parse("max_tokens: 4096")
        assert r.is_success
        assert r.value == 4096

    def test_key_value_string_result(self):
        p = KeyValParser()
        r = p.parse("display_name: some_value")
        assert r.is_success
        assert r.value == "some_value"

    def test_float_value(self):
        p = KeyValParser()
        r = p.parse("ratio: 0.75")
        assert r.is_success
        assert r.value == 0.75

    def test_not_found(self):
        p = KeyValParser()
        r = p.parse("NOT_FOUND")
        assert r.not_found

    def test_descriptive_labels_skipped(self):
        """FIELD_NAME: and VALUE: are descriptive labels, skip them.
        A real field in the same text should be found."""
        p = KeyValParser()
        r = p.parse("FIELD_NAME: max_tokens\nVALUE: 4096\nmax_tokens: 8192")
        assert r.is_success
        assert r.value == 8192

    def test_multiline_with_kv(self):
        p = KeyValParser()
        r = p.parse(
            "After analysis of the data:\n"
            "The field you're looking for is:\n"
            "max_context_length: 8192\n"
            "I believe this is the correct answer."
        )
        assert r.is_success
        assert r.value == 8192


class TestNumericParser:
    def test_integer_in_text(self):
        p = NumericParser()
        r = p.parse("The value is 4096 here")
        assert r.is_success
        assert r.value == 4096

    def test_float_in_text(self):
        p = NumericParser()
        r = p.parse("The score is 0.75 overall")
        assert r.is_success
        assert r.value == 0.75

    def test_no_number(self):
        p = NumericParser()
        r = p.parse("No numbers here at all")
        assert r.not_found


class TestJSONParser:
    def test_valid_json_object(self):
        p = JSONParser()
        r = p.parse('{"max_tokens": 4096}')
        assert r.is_success
        assert r.value == 4096

    def test_json_string_value(self):
        p = JSONParser()
        r = p.parse('{"result": "hello"}')
        assert r.is_success
        assert r.value == "hello"

    def test_json_with_nested_object(self):
        p = JSONParser()
        r = p.parse('{"data": {"tokens": 8192}}')
        assert r.is_success
        assert r.value == 8192

    def test_invalid_json(self):
        p = JSONParser()
        r = p.parse("This is not json")
        assert r.not_found

    def test_json_array(self):
        p = JSONParser()
        r = p.parse('[42]')
        assert r.is_success
        assert r.value == 42
