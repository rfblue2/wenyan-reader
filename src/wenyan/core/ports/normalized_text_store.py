from pathlib import Path
from typing import Protocol

from wenyan_models.artifacts.normalized import NormalizedDocument
from wenyan_models.domain.ids import ContentHash, DocumentId
from wenyan_models.sources import DocumentYaml


class NormalizedTextStore(Protocol):
    def text_path(self, document_id: DocumentId) -> Path: ...

    def character_count(self, document_id: DocumentId) -> int: ...

    def read_slice(self, document_id: DocumentId, start: int, end: int) -> str: ...

    def verify_hash(self, document_id: DocumentId, expected: ContentHash) -> bool: ...

    def write_from_source(
        self,
        document_id: DocumentId,
        title: str,
        source_path: Path,
        metadata: DocumentYaml,
    ) -> NormalizedDocument: ...
