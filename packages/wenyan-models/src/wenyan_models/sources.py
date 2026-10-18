from pydantic import BaseModel, Field

from wenyan_models.base import DEFAULT_ARTIFACT_CONFIG
from wenyan_models.domain.ids import DocumentId, Slug


class RegistryEntry(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    slug: Slug
    title: str
    document_id: DocumentId | None = None


class DocumentYaml(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    title: str
    language: str | None = None
    script: str | None = None
    provenance: str | None = None
    normalization: dict[str, object] = Field(default_factory=dict)
    source_headings: dict[str, object] = Field(default_factory=dict, alias="sourceHeadings")
