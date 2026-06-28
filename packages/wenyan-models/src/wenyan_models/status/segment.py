from pydantic import BaseModel, Field

from wenyan_models.artifacts.base import (
    DEFAULT_ARTIFACT_CONFIG,
    ChapterIdField,
    DocumentIdField,
    ParagraphIdField,
    SegmentIdField,
)
from wenyan_models.domain.enums import UnitStatus
from wenyan_models.status.common import ScopeSegment
from wenyan_models.status.component import ComponentStatusItem


class SegmentStatus(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    document_id: DocumentIdField = Field(alias="documentId")
    chapter_id: ChapterIdField = Field(alias="chapterId")
    paragraph_id: ParagraphIdField = Field(alias="paragraphId")
    segment_id: SegmentIdField = Field(alias="segmentId")
    scope: ScopeSegment
    text: str
    status: UnitStatus
    components: tuple[ComponentStatusItem, ...] = ()
