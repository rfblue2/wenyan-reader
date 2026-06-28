from pydantic import BaseModel, Field

from wenyan_models.artifacts.base import (
    DEFAULT_ARTIFACT_CONFIG,
    ChapterIdField,
    DocumentIdField,
)
from wenyan_models.domain.enums import UnitStatus
from wenyan_models.status.common import ParagraphProgress, ScopeChapter, StatusCounts


class ParagraphStatusItem(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    paragraph_id: str = Field(alias="paragraphId")
    ordinal: int
    status: UnitStatus
    progress: ParagraphProgress | None = None


class ChapterStatus(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    document_id: DocumentIdField = Field(alias="documentId")
    chapter_id: ChapterIdField = Field(alias="chapterId")
    scope: ScopeChapter
    counts: StatusCounts
    paragraphs: tuple[ParagraphStatusItem, ...] = ()
