from typing import Protocol

from wenyan_models.domain.ids import (
    ChapterId,
    DocumentId,
    ParagraphId,
    SegmentId,
)
from wenyan_models.status.document import DocumentStatus


class StatusReader(Protocol):
    def document_status(self, document_id: DocumentId) -> DocumentStatus: ...

    def chapter_status(self, document_id: DocumentId, chapter_id: ChapterId) -> DocumentStatus: ...

    def paragraph_status(
        self,
        document_id: DocumentId,
        paragraph_id: ParagraphId,
    ) -> DocumentStatus: ...

    def segment_status(
        self,
        document_id: DocumentId,
        segment_id: SegmentId,
    ) -> DocumentStatus: ...
