from dataclasses import dataclass
from typing import TypeAlias

from wenyan_models.domain.ids import DocumentId


@dataclass(frozen=True)
class PromptTextSlice:
    document_id: DocumentId
    start: int
    end: int


PromptContextValue: TypeAlias = str | PromptTextSlice
