from pydantic import BaseModel, Field

from wenyan_models.artifacts.base import (
    DEFAULT_ARTIFACT_CONFIG,
    ChapterIdField,
    ContentHashField,
    DocumentIdField,
    ParagraphIdField,
    PromptVersionField,
)
from wenyan_models.domain.enums import ValidationStatus
from wenyan_models.domain.validation import CheckResult


class ChapterProposalItem(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    id: ChapterIdField
    title: str
    start: int
    end: int
    rationale: str


class ChapterProposal(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    document_id: DocumentIdField = Field(alias="documentId")
    model: str
    prompt_version: PromptVersionField = Field(alias="promptVersion")
    input_hash: ContentHashField = Field(alias="inputHash")
    attempts: int
    source_hash: ContentHashField = Field(alias="sourceHash")
    chapters: tuple[ChapterProposalItem, ...]


class ParagraphProposalItem(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    id: ParagraphIdField
    start: int
    end: int
    rationale: str


class ParagraphProposal(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    document_id: DocumentIdField = Field(alias="documentId")
    chapter_id: ChapterIdField = Field(alias="chapterId")
    model: str
    prompt_version: PromptVersionField = Field(alias="promptVersion")
    input_hash: ContentHashField = Field(alias="inputHash")
    attempts: int
    chapter_text_hash: ContentHashField = Field(alias="chapterTextHash")
    paragraphs: tuple[ParagraphProposalItem, ...]


class SpanValidationArtifact(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    status: ValidationStatus
    checks: tuple[CheckResult, ...] = ()
