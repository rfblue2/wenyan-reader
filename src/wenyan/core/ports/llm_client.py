from typing import Protocol

from pydantic import BaseModel


class LLMParseError(RuntimeError):
    pass


class StructuredPrompt(Protocol):
    @property
    def template_name(self) -> str: ...

    def render(self) -> str: ...

    def context_value(self, key: str) -> str: ...


class LLMClient(Protocol):
    def complete_model[T: BaseModel](
        self,
        prompt: StructuredPrompt,
        model: type[T],
    ) -> T: ...
