from typing import Protocol

from wenyan_models.domain.ids import (
    ChapterId,
    DocumentId,
    ParagraphId,
    SegmentId,
)
from wenyan_models.status.chapter import ChapterStatus
from wenyan_models.status.document import DocumentStatus
from wenyan_models.status.paragraph import ParagraphStatus
from wenyan_models.status.segment import SegmentStatus


class StatusReader(Protocol):
    def document_status(self, document_id: DocumentId) -> DocumentStatus: ...

    def chapter_status(self, document_id: DocumentId, chapter_id: ChapterId) -> ChapterStatus: ...

    def paragraph_status(
        self,
        document_id: DocumentId,
        paragraph_id: ParagraphId,
    ) -> ParagraphStatus: ...

    def segment_status(
        self,
        document_id: DocumentId,
        segment_id: SegmentId,
    ) -> SegmentStatus: ...
