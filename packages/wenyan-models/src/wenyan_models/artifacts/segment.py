from typing import Literal

from pydantic import BaseModel, Field

from wenyan_models.base import DEFAULT_ARTIFACT_CONFIG
from wenyan_models.domain.enums import ReviewStatus
from wenyan_models.domain.ids import (
    ChapterIdField,
    ContentHashField,
    DocumentIdField,
    ParagraphIdField,
    SegmentIdField,
)
from wenyan_models.domain.review import ReviewFinding


class SegmentLocalContext(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    paragraph_summary: str = Field(default="", alias="paragraphSummary")
    previous_segment: str | None = Field(default=None, alias="previousSegment")
    next_segment: str | None = Field(default=None, alias="nextSegment")


class NoteItem(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    id: str
    anchor_token_ids: tuple[str, ...] = Field(alias="anchorTokenIds")
    body: str


class NoteCitation(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    label: str
    excerpt: str
    url: str = ""
    accessed_at: str = Field(default="", alias="accessedAt")


class ContextNoteItem(NoteItem):
    sources: tuple[NoteCitation, ...] = ()


class SourceGroundingItem(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    note_id: str = Field(alias="noteId")
    supported: bool
    source_indexes: tuple[int, ...] = Field(default=(), alias="sourceIndexes")


class SegmentArtifact(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    segment_id: SegmentIdField = Field(alias="segmentId")
    model: str
    input_hash: ContentHashField = Field(alias="inputHash")
    attempts: int


class SegmentReview(SegmentArtifact):
    status: ReviewStatus
    findings: tuple[ReviewFinding, ...] = ()


class SegmentInput(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    document_id: DocumentIdField = Field(alias="documentId")
    chapter_id: ChapterIdField = Field(alias="chapterId")
    paragraph_id: ParagraphIdField = Field(alias="paragraphId")
    segment_id: SegmentIdField = Field(alias="segmentId")
    segment_text: str = Field(alias="segmentText")
    local_context: SegmentLocalContext = Field(
        default_factory=SegmentLocalContext,
        alias="localContext",
    )


class TokenItem(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    id: str
    surface: str
    start: int
    end: int


class TokenizationArtifact(SegmentArtifact):
    text: str
    tokens: tuple[TokenItem, ...]


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


class GlossesArtifact(SegmentArtifact):
    gloss_decisions: tuple[GlossDecision, ...] = Field(default=(), alias="glossDecisions")
    new_gloss_ids: tuple[str, ...] = Field(default=(), alias="newGlossIds")
    new_glosses: tuple[GlossEntry, ...] = Field(default=(), alias="newGlosses")


class GrammarNotesArtifact(SegmentArtifact):
    grammar_notes: tuple[NoteItem, ...] = Field(default=(), alias="grammarNotes")


class ContextNotesArtifact(SegmentArtifact):
    context_notes: tuple[ContextNoteItem, ...] = Field(default=(), alias="contextNotes")


class ContextReviewArtifact(SegmentReview):
    source_grounding: tuple[SourceGroundingItem, ...] = Field(default=(), alias="sourceGrounding")
