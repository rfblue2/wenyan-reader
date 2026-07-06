from collections.abc import Mapping
from typing import Protocol

from wenyan.core.ports.llm_client import StructuredPrompt
from wenyan.core.ports.normalized_text_store import NormalizedTextStore
from wenyan.core.ports.prompt_context import PromptContextValue


class PromptLoader(Protocol):
    def build_prompt(
        self,
        template_name: str,
        context: Mapping[str, PromptContextValue],
        *,
        normalized_text: NormalizedTextStore | None = None,
    ) -> StructuredPrompt: ...
