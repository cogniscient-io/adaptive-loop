import os
import tempfile

import pytest

from adaptive_loop.messages.registry import PromptRegistry
from adaptive_loop.messages.template import PromptTemplate
from adaptive_loop.exceptions import TemplateError


@pytest.fixture
def registry():
    return PromptRegistry()


class TestPromptRegistryGet:
    def test_get_by_name(self, registry):
        t = PromptTemplate(name="hello", user="Hi {name}")
        registry.register(t)
        assert registry.get("hello") is t

    def test_get_missing_raises(self, registry):
        with pytest.raises(TemplateError, match="not found"):
            registry.get("missing")


class TestPromptRegistryLoadDirectory:
    def test_load_yaml_file(self, registry):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "test.yaml")
            with open(path, "w") as f:
                f.write(
                    "name: my_prompt\n"
                    "user: Find {field} in {context}.\n"
                    "parser_chain:\n"
                    "  - key_value\n"
                    "  - numeric\n"
                )
            registry.load_directory(d)

        template = registry.get("my_prompt")
        assert isinstance(template, PromptTemplate)
        assert template.user == "Find {field} in {context}."
        assert template.parser_chain == ["key_value", "numeric"]

    def test_load_with_system(self, registry):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "sys.yaml")
            with open(path, "w") as f:
                f.write(
                    "name: with_system\n"
                    "system: You are helpful.\n"
                    "user: Hello.\n"
                )
            registry.load_directory(d)

        template = registry.get("with_system")
        assert template.system == "You are helpful."

    def test_override_same_name(self, registry):
        with tempfile.TemporaryDirectory() as d1:
            path = os.path.join(d1, "base.yaml")
            with open(path, "w") as f:
                f.write("name: greet\nuser: Hello.")
            registry.load_directory(d1)

        with tempfile.TemporaryDirectory() as d2:
            path = os.path.join(d2, "override.yaml")
            with open(path, "w") as f:
                f.write("name: greet\nuser: Hi there.")
            registry.load_directory(d2)

        assert registry.get("greet").user == "Hi there."

    def test_ignore_non_yaml_files(self, registry):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "readme.txt"), "w") as f:
                f.write("not yaml")
            with open(os.path.join(d, "script.py"), "w") as f:
                f.write("print(1)")
            registry.load_directory(d)

    def test_skips_empty_name(self, registry):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "no_name.yaml")
            with open(path, "w") as f:
                f.write("user: no name here\n")
            registry.load_directory(d)


class TestPromptRegistryGetSystem:
    def test_returns_system_message(self, registry):
        t = PromptTemplate(
            name="with_sys", system="Be polite.", user="Hi {name}"
        )
        registry.register(t)
        assert registry.get_system("with_sys") == "Be polite."

    def test_returns_none_when_missing(self, registry):
        t = PromptTemplate(name="no_sys", user="Hi")
        registry.register(t)
        assert registry.get_system("no_sys") is None
