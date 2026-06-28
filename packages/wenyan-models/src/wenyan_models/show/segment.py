from typing import Literal

from pydantic import BaseModel, Field

from wenyan_models.artifacts.base import (
    DEFAULT_ARTIFACT_CONFIG,
    ChapterIdField,
    DocumentIdField,
    ParagraphIdField,
    SegmentIdField,
)
from wenyan_models.domain.enums import ComponentKind, ReviewStatus, UnitStatus
from wenyan_models.status.component import ComponentStatusItem


class TokenGlossRow(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    token_id: str = Field(alias="tokenId")
    surface: str
    pinyin: str | None = None
    gloss: str | None = None
    decision: Literal["reuse-existing", "create-new"] | None = None


class ReviewShowItem(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    kind: ComponentKind
    status: ReviewStatus
    findings: tuple[dict[str, object], ...] = ()


class SegmentShowView(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    document_id: DocumentIdField = Field(alias="documentId")
    document_ref: str = Field(alias="documentRef")
    chapter_id: ChapterIdField = Field(alias="chapterId")
    chapter_handle: str | None = Field(default=None, alias="chapterHandle")
    paragraph_id: ParagraphIdField = Field(alias="paragraphId")
    paragraph_handle: str | None = Field(default=None, alias="paragraphHandle")
    segment_id: SegmentIdField = Field(alias="segmentId")
    segment_handle: str | None = Field(default=None, alias="segmentHandle")
    text: str
    status: UnitStatus
    tokens: tuple[TokenGlossRow, ...] = ()
    reviews: tuple[ReviewShowItem, ...] = ()
    components: tuple[ComponentStatusItem, ...] = ()
