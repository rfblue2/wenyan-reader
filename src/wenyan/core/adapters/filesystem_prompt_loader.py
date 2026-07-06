from collections.abc import Mapping
from pathlib import Path

from wenyan.core.adapters.prompt_template import RenderedPrompt, load_prompt_template
from wenyan.core.ports.llm_client import StructuredPrompt
from wenyan.core.ports.normalized_text_store import NormalizedTextStore
from wenyan.core.ports.prompt_context import PromptContextValue
from wenyan.core.ports.prompt_loader import PromptLoader


class FilesystemPromptLoader(PromptLoader):
    def __init__(self, prompts_root: Path) -> None:
        self._prompts_root = prompts_root

    def build_prompt(
        self,
        template_name: str,
        context: Mapping[str, PromptContextValue],
        *,
        normalized_text: NormalizedTextStore | None = None,
    ) -> StructuredPrompt:
        template = load_prompt_template(self._prompts_root, template_name)
        return RenderedPrompt(template, context, normalized_text=normalized_text)
