import pytest

from adaptive_loop.messages.template import PromptTemplate


class TestPromptTemplate:
    def test_render_with_dict(self):
        template = PromptTemplate(
            name="greet",
            user="Hello {name}, welcome to {place}.",
        )
        rendered = template.render({"name": "Alice", "place": "town"})
        assert rendered == "Hello Alice, welcome to town."

    def test_render_with_kwargs(self):
        template = PromptTemplate(
            name="greet",
            user="Hello {name}.",
        )
        rendered = template.render(name="Bob")
        assert rendered == "Hello Bob."

    def test_render_kwargs_override_values(self):
        """Kwargs take precedence over values dict."""
        template = PromptTemplate(
            name="greet",
            user="Hello {name}.",
        )
        rendered = template.render({"name": "Alice"}, name="Bob")
        assert rendered == "Hello Bob."

    def test_render_missing_key_raises(self):
        template = PromptTemplate(
            name="greet",
            user="Hello {name}.",
        )
        with pytest.raises(ValueError, match="Missing"):
            template.render({})

    def test_system_message(self):
        template = PromptTemplate(
            name="greet",
            system="You are polite.",
            user="Hello {name}.",
            parser_chain=["key_value"],
        )
        assert template.system == "You are polite."

    def test_parser_chain_default(self):
        template = PromptTemplate(name="t", user="x")
        assert template.parser_chain == []

    def test_parser_chain_set(self):
        template = PromptTemplate(
            name="t",
            user="x",
            parser_chain=["key_value", "numeric"],
        )
        assert template.parser_chain == ["key_value", "numeric"]

    def test_render_only_user_returned(self):
        """render() returns only the user message, not system."""
        template = PromptTemplate(
            name="t",
            system="Always be helpful.",
            user="Find {field} in {context}.",
        )
        rendered = template.render(field="X", context="data")
        assert rendered == "Find X in data."
        assert "Always be helpful" not in rendered

    def test_render_multiline_template(self):
        template = PromptTemplate(
            name="multi",
            user="Line1: {a}\nLine2: {b}",
        )
        rendered = template.render({"a": "hello", "b": "world"})
        assert "Line1: hello" in rendered
        assert "Line2: world" in rendered
