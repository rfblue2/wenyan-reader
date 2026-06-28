from collections.abc import Mapping
from typing import Protocol

from pydantic import BaseModel

from wenyan_models.domain.ids import PromptVersion


class StructuredPrompt(Protocol):
    @property
    def prompt_version(self) -> PromptVersion: ...

    @property
    def template_name(self) -> str: ...

    def render(self, context: Mapping[str, str]) -> str: ...


class LLMClient(Protocol):
    def complete_model[T: BaseModel](self, prompt: StructuredPrompt, model: type[T]) -> T: ...
