from pydantic import BaseModel, Field

from wenyan_models.artifacts.base import (
    DEFAULT_ARTIFACT_CONFIG,
    ContentHashField,
    DocumentIdField,
)

DEFAULT_NORMALIZED_TEXT_PATH = "normalized-text.txt"
DEFAULT_TEXT_INDEX_STRIDE = 65_536


class NormalizationInfo(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    encoding: str
    punctuation_policy: str = Field(alias="punctuationPolicy")
    notes: tuple[str, ...] = ()


class TextByteIndex(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    stride: int = DEFAULT_TEXT_INDEX_STRIDE
    byte_offsets: tuple[int, ...] = Field(alias="byteOffsets")


class NormalizedDocument(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    document_id: DocumentIdField = Field(alias="documentId")
    title: str
    source_hash: ContentHashField = Field(alias="sourceHash")
    normalized_hash: ContentHashField = Field(alias="normalizedHash")
    text_path: str = Field(default=DEFAULT_NORMALIZED_TEXT_PATH, alias="textPath")
    character_count: int = Field(alias="characterCount")
    text_index: TextByteIndex = Field(alias="textIndex")
    normalization: NormalizationInfo
