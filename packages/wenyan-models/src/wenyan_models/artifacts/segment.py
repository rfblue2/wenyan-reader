from typing import Literal

from pydantic import BaseModel, Field

from wenyan_models.artifacts.base import (
    DEFAULT_ARTIFACT_CONFIG,
    ChapterIdField,
    ContentHashField,
    DocumentIdField,
    ParagraphIdField,
    SegmentIdField,
)
from wenyan_models.domain.enums import ReviewStatus


class NoteSource(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    source_id: str = Field(alias="sourceId")
    label: str
    detail: str = ""


class NoteItem(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    id: str
    type: Literal["grammar", "context"]
    anchor_token_ids: tuple[str, ...] = Field(alias="anchorTokenIds")
    body: str
    sources: tuple[NoteSource, ...] = ()


class SourceGroundingItem(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    note_id: str = Field(alias="noteId")
    supported: bool
    source_ids: tuple[str, ...] = Field(default=(), alias="sourceIds")


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
    input_hash: ContentHashField = Field(alias="inputHash")
    attempts: int
    text: str
    tokens: tuple[TokenItem, ...]


class TokenizationReviewArtifact(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    segment_id: SegmentIdField = Field(alias="segmentId")
    model: str
    input_hash: ContentHashField = Field(alias="inputHash")
    attempts: int
    status: ReviewStatus
    findings: tuple[dict[str, object], ...] = ()


class GlossEntry(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    id: str
    surface: str
    pinyin: str
    gloss: str


class GlossDecision(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    token_id: str = Field(alias="tokenId")
    gloss_id: str = Field(alias="glossId")
    decision: Literal["reuse-existing", "create-new"]


class GlossesArtifact(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    segment_id: SegmentIdField = Field(alias="segmentId")
    model: str
    input_hash: ContentHashField = Field(alias="inputHash")
    attempts: int
    gloss_decisions: tuple[GlossDecision, ...] = Field(default=(), alias="glossDecisions")
    new_gloss_ids: tuple[str, ...] = Field(default=(), alias="newGlossIds")
    new_glosses: tuple[GlossEntry, ...] = Field(default=(), alias="newGlosses")


class GlossReviewArtifact(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    segment_id: SegmentIdField = Field(alias="segmentId")
    model: str
    input_hash: ContentHashField = Field(alias="inputHash")
    attempts: int
    status: ReviewStatus
    findings: tuple[dict[str, object], ...] = ()


class GrammarNotesArtifact(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    segment_id: SegmentIdField = Field(alias="segmentId")
    model: str
    input_hash: ContentHashField = Field(alias="inputHash")
    attempts: int
    grammar_notes: tuple[NoteItem, ...] = Field(default=(), alias="grammarNotes")


class GrammarReviewArtifact(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    segment_id: SegmentIdField = Field(alias="segmentId")
    model: str
    input_hash: ContentHashField = Field(alias="inputHash")
    attempts: int
    status: ReviewStatus
    findings: tuple[dict[str, object], ...] = ()


class ContextNotesArtifact(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    segment_id: SegmentIdField = Field(alias="segmentId")
    model: str
    input_hash: ContentHashField = Field(alias="inputHash")
    attempts: int
    context_notes: tuple[NoteItem, ...] = Field(default=(), alias="contextNotes")


class ContextReviewArtifact(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    segment_id: SegmentIdField = Field(alias="segmentId")
    model: str
    input_hash: ContentHashField = Field(alias="inputHash")
    attempts: int
    status: ReviewStatus
    findings: tuple[dict[str, object], ...] = ()
    source_grounding: tuple[SourceGroundingItem, ...] = Field(default=(), alias="sourceGrounding")
