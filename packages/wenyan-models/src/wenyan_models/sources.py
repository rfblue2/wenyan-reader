from pydantic import BaseModel, ConfigDict, Field

from wenyan_models.domain.ids import DocumentId, Slug

_DEFAULT_MODEL_CONFIG = ConfigDict(frozen=True, populate_by_name=True, extra="forbid")


class RegistryEntry(BaseModel):
    model_config = _DEFAULT_MODEL_CONFIG

    slug: Slug
    title: str
    document_id: DocumentId | None = None


class DocumentYaml(BaseModel):
    model_config = _DEFAULT_MODEL_CONFIG

    title: str
    language: str | None = None
    script: str | None = None
    provenance: str | None = None
    normalization: dict[str, object] = Field(default_factory=dict)
    source_headings: dict[str, object] = Field(default_factory=dict, alias="sourceHeadings")
