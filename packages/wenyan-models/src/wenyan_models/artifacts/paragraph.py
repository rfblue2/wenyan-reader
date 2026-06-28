from pydantic import BaseModel, Field

from wenyan_models.artifacts.base import (
    DEFAULT_ARTIFACT_CONFIG,
    ContentHashField,
    ParagraphIdField,
    SegmentIdField,
)
from wenyan_models.domain.enums import ValidationStatus
from wenyan_models.domain.validation import CheckResult


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
    paragraph_context_notes: tuple[dict[str, object], ...] = Field(
        default=(),
        alias="paragraphContextNotes",
    )
    draft_rationale: dict[str, object] = Field(default_factory=dict, alias="draftRationale")


class ParagraphValidationArtifact(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    status: ValidationStatus
    checks: tuple[CheckResult, ...] = ()
