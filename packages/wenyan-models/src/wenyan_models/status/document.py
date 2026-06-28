from pydantic import BaseModel, Field

from wenyan_models.artifacts.base import DEFAULT_ARTIFACT_CONFIG, DocumentIdField
from wenyan_models.domain.enums import UnitStatus
from wenyan_models.status.common import (
    ChapterProgress,
    ScopeDocument,
    StatusCounts,
)


class DocumentSourceStatus(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    status: str
    normalized_document_path: str = Field(alias="normalizedDocumentPath")
    source_hash: str = Field(alias="sourceHash")
    normalized_hash: str = Field(alias="normalizedHash")


class ChapterStatusItem(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    chapter_id: str = Field(alias="chapterId")
    title: str
    status: UnitStatus
    progress: ChapterProgress | None = None


class DocumentStatus(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    document_id: DocumentIdField = Field(alias="documentId")
    title: str
    scope: ScopeDocument
    source: DocumentSourceStatus
    counts: StatusCounts
    chapters: tuple[ChapterStatusItem, ...] = ()
