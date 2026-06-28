from pydantic import BaseModel, Field

from wenyan_models.artifacts.base import (
    DEFAULT_ARTIFACT_CONFIG,
    ChapterIdField,
    ContentHashField,
    DocumentIdField,
    ParagraphIdField,
    PromptVersionField,
    SegmentIdField,
)
from wenyan_models.domain.enums import ReviewStatus


class SegmentInput(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    document_id: DocumentIdField = Field(alias="documentId")
    chapter_id: ChapterIdField = Field(alias="chapterId")
    paragraph_id: ParagraphIdField = Field(alias="paragraphId")
    segment_id: SegmentIdField = Field(alias="segmentId")
    segment_text: str = Field(alias="segmentText")
    local_context: dict[str, object] = Field(default_factory=dict, alias="localContext")
    candidate_glosses: tuple[dict[str, object], ...] = Field(
        default=(),
        alias="candidateGlosses",
    )
    source_snippets: tuple[dict[str, object], ...] = Field(default=(), alias="sourceSnippets")


class TokenItem(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    id: str
    surface: str
    start: int
    end: int


class TokenizationArtifact(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    segment_id: SegmentIdField = Field(alias="segmentId")
    model: str
    prompt_version: PromptVersionField = Field(alias="promptVersion")
    input_hash: ContentHashField = Field(alias="inputHash")
    attempts: int
    text: str
    tokens: tuple[TokenItem, ...]


class TokenizationReviewArtifact(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    segment_id: SegmentIdField = Field(alias="segmentId")
    model: str
    prompt_version: PromptVersionField = Field(alias="promptVersion")
    input_hash: ContentHashField = Field(alias="inputHash")
    attempts: int
    status: ReviewStatus
    findings: tuple[dict[str, object], ...] = ()
