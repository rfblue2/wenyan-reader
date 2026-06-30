from pydantic import BaseModel, Field

from wenyan_models.artifacts.base import (
    DEFAULT_ARTIFACT_CONFIG,
    ChapterIdField,
    DocumentIdField,
    ParagraphIdField,
)
from wenyan_models.domain.enums import ComponentKind, UnitStatus
from wenyan_models.status.common import ScopeParagraph, SegmentProgress, StatusCounts
from wenyan_models.status.component import ComponentStatusItem


class ParagraphStructureStatus(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    status: UnitStatus
    segment_count: int | None = Field(default=None, alias="segmentCount")


class SegmentStatusItem(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    segment_id: str = Field(alias="segmentId")
    ordinal: int
    status: UnitStatus
    text_preview: str = Field(alias="textPreview")
    progress: SegmentProgress | None = None
    blocked_component: ComponentKind | None = Field(default=None, alias="blockedComponent")


class ParagraphAssemblyStatus(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    assemble: ComponentStatusItem
    review: ComponentStatusItem


class ParagraphStatus(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    document_id: DocumentIdField = Field(alias="documentId")
    chapter_id: ChapterIdField = Field(alias="chapterId")
    paragraph_id: ParagraphIdField = Field(alias="paragraphId")
    scope: ScopeParagraph
    structure: ParagraphStructureStatus
    counts: StatusCounts
    segments: tuple[SegmentStatusItem, ...] = ()
    assembly: ParagraphAssemblyStatus | None = None
