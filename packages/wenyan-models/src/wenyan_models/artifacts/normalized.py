from pydantic import BaseModel, Field

from wenyan_models.artifacts.base import (
    DEFAULT_ARTIFACT_CONFIG,
    ContentHashField,
    DocumentIdField,
)


class NormalizationInfo(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    encoding: str
    punctuation_policy: str = Field(alias="punctuationPolicy")
    notes: tuple[str, ...] = ()


class NormalizedDocument(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    document_id: DocumentIdField = Field(alias="documentId")
    title: str
    source_hash: ContentHashField = Field(alias="sourceHash")
    normalized_hash: ContentHashField = Field(alias="normalizedHash")
    text: str
    normalization: NormalizationInfo
