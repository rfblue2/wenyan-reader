from pydantic import BaseModel, Field

from wenyan_models.artifacts.segment import NoteCitation
from wenyan_models.base import DEFAULT_ARTIFACT_CONFIG
from wenyan_models.domain.ids import ContentHashField, ParagraphIdField, SegmentIdField


class ParagraphContextNote(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    id: str
    anchor_segment_ids: tuple[str, ...] = Field(alias="anchorSegmentIds")
    body: str
    sources: tuple[NoteCitation | str, ...] = ()


class ParagraphDraftSegment(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    id: SegmentIdField
    text: str


class ParagraphDraft(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    paragraph_id: ParagraphIdField = Field(alias="paragraphId")
    model: str
    input_hash: ContentHashField = Field(alias="inputHash")
    attempts: int
    segments: tuple[ParagraphDraftSegment, ...]
    paragraph_context_notes: tuple[ParagraphContextNote, ...] = Field(
        default=(),
        alias="paragraphContextNotes",
    )
    draft_rationale: dict[str, object] = Field(default_factory=dict, alias="draftRationale")
