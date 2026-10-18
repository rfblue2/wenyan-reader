from typing import Protocol

from pydantic import BaseModel

from wenyan.core.ports.artifact_ref import ArtifactRef
from wenyan_models.base import DEFAULT_ARTIFACT_CONFIG
from wenyan_models.domain.ids import ChapterId, DocumentId, ParagraphId, SegmentId


class ValidationIssue(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    code: str
    message: str
    ref: ArtifactRef | None = None


class GraphValidationReport(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    issues: tuple[ValidationIssue, ...]

    @property
    def ok(self) -> bool:
        return len(self.issues) == 0


class GraphValidator(Protocol):
    def validate_document(self, document_id: DocumentId) -> GraphValidationReport: ...

    def validate_chapter(
        self,
        document_id: DocumentId,
        chapter_id: ChapterId,
    ) -> GraphValidationReport: ...

    def validate_paragraph(
        self,
        document_id: DocumentId,
        paragraph_id: ParagraphId,
    ) -> GraphValidationReport: ...

    def validate_segment(
        self,
        document_id: DocumentId,
        segment_id: SegmentId,
    ) -> GraphValidationReport: ...
