import os
from typing import Any, Dict, Optional

import yaml

from adaptive_loop.exceptions import TemplateError
from adaptive_loop.messages.template import PromptTemplate


class PromptRegistry:
    def __init__(self):
        self._templates: Dict[str, PromptTemplate] = {}

    def register(self, template: PromptTemplate):
        self._templates[template.name] = template

    def get(self, name: str) -> PromptTemplate:
        tpl = self._templates.get(name)
        if tpl is None:
            raise TemplateError(
                f"Prompt template '{name}' not found in registry"
            )
        return tpl

    def get_system(self, name: str) -> Optional[str]:
        tpl = self._templates.get(name)
        return tpl.system if tpl else None

    def load_directory(self, path: str):
        if not os.path.isdir(path):
            return
        for filename in sorted(os.listdir(path)):
            if not filename.endswith((".yaml", ".yml")):
                continue
            filepath = os.path.join(path, filename)
            if not os.path.isfile(filepath):
                continue
            self._load_yaml_file(filepath)

    def _load_yaml_file(self, filepath: str):
        with open(filepath, "r") as f:
            data = yaml.safe_load(f)
        if not isinstance(data, dict) or "name" not in data or not data.get(
            "user"
        ):
            return
        self.register(
            PromptTemplate(
                name=data["name"],
                user=data["user"],
                system=data.get("system"),
                parser_chain=data.get("parser_chain") or [],
            )
        )
