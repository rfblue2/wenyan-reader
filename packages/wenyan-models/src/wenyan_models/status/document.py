from typing import Literal

from pydantic import BaseModel, Field

from wenyan_models.artifacts.base import DEFAULT_ARTIFACT_CONFIG, DocumentIdField
from wenyan_models.domain.enums import ComponentKind, UnitStatus


class ScopeDocument(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    type: Literal["document"] = "document"


class DocumentSourceStatus(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    status: str
    normalized_document_path: str = Field(alias="normalizedDocumentPath")
    source_hash: str = Field(alias="sourceHash")
    normalized_hash: str = Field(alias="normalizedHash")


class StatusCounts(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    complete: int = 0
    in_progress: int = Field(default=0, alias="inProgress")
    pending: int = 0
    failed: int = 0
    blocked: int = 0


class ChapterStatusItem(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    chapter_id: str = Field(alias="chapterId")
    title: str
    status: UnitStatus


class DocumentStatus(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    document_id: DocumentIdField = Field(alias="documentId")
    title: str
    scope: ScopeDocument
    source: DocumentSourceStatus
    counts: StatusCounts
    chapters: tuple[ChapterStatusItem, ...] = ()


class ComponentStatusItem(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    kind: ComponentKind
    status: UnitStatus
    artifact_path: str | None = Field(default=None, alias="artifactPath")
