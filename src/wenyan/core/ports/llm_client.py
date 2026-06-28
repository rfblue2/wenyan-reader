from typing import Protocol

from pydantic import BaseModel


class StructuredPrompt(Protocol):
    @property
    def template_name(self) -> str: ...

    def render(self, context: dict[str, str]) -> str: ...


class LLMClient(Protocol):
    def complete_model[T: BaseModel](
        self,
        prompt: StructuredPrompt,
        model: type[T],
    ) -> T: ...
