from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from wenyan.core.ports.llm_client import StructuredPrompt
from wenyan.core.ports.normalized_text_store import NormalizedTextStore
from wenyan.core.ports.prompt_context import PromptContextValue, PromptTextSlice


class PromptTemplate(BaseModel):
    model_config = ConfigDict(frozen=True, populate_by_name=True, extra="forbid")

    name: str
    body: str

    @property
    def template_name(self) -> str:
        return self.name

    def render(self, context: Mapping[str, str]) -> str:
        rendered = self.body
        for key, value in context.items():
            rendered = rendered.replace(f"{{{{{key}}}}}", value)
        return rendered


@dataclass(frozen=True)
class RenderedPrompt(StructuredPrompt):
    template: PromptTemplate
    context: Mapping[str, PromptContextValue]
    normalized_text: NormalizedTextStore | None = None

    @property
    def template_name(self) -> str:
        return self.template.template_name

    def render(self, context: Mapping[str, str]) -> str:
        materialized = {key: self._materialize(value) for key, value in self.context.items()}
        return self.template.render(materialized)

    def context_value(self, key: str) -> str:
        if key not in self.context:
            raise ValueError(f"missing prompt context key: {key}")
        return self._materialize(self.context[key])

    def _materialize(self, value: PromptContextValue) -> str:
        if isinstance(value, str):
            return value
        if self.normalized_text is None:
            raise ValueError("prompt context requires normalized text store")
        if isinstance(value, PromptTextSlice):
            return self.normalized_text.read_slice(value.document_id, value.start, value.end)
        raise TypeError(f"unsupported prompt context value: {type(value)!r}")


def load_prompt_template(prompts_root: Path, template_name: str) -> PromptTemplate:
    path = prompts_root / f"{template_name}.md"
    if not path.is_file():
        raise ValueError(f"prompt template not found: {path}")
    return PromptTemplate(
        name=template_name,
        body=path.read_text(encoding="utf-8"),
    )
