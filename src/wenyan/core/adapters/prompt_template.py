from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from wenyan_models.domain.ids import PromptVersion, prompt_version


class PromptTemplate(BaseModel):
    model_config = ConfigDict(frozen=True, populate_by_name=True, extra="forbid")

    name: str
    version: str
    body: str

    @property
    def prompt_version(self) -> PromptVersion:
        return prompt_version(self.version)

    @property
    def template_name(self) -> str:
        return self.name

    def render(self, context: Mapping[str, str]) -> str:
        rendered = self.body
        for key, value in context.items():
            rendered = rendered.replace(f"{{{{{key}}}}}", value)
        return rendered


@dataclass(frozen=True)
class RenderedPrompt:
    template: PromptTemplate
    context: Mapping[str, str]

    @property
    def prompt_version(self) -> PromptVersion:
        return self.template.prompt_version

    @property
    def template_name(self) -> str:
        return self.template.template_name

    def render(self, context: Mapping[str, str]) -> str:
        return self.template.render(self.context)

    def context_value(self, key: str) -> str:
        if key not in self.context:
            raise ValueError(f"missing prompt context key: {key}")
        return self.context[key]


def load_prompt_template(prompts_root: Path, template_name: str, version: str) -> PromptTemplate:
    path = prompts_root / f"{template_name}-{version}.md"
    if not path.is_file():
        raise ValueError(f"prompt template not found: {path}")
    return PromptTemplate(
        name=template_name,
        version=f"{template_name}-{version}",
        body=path.read_text(encoding="utf-8"),
    )
