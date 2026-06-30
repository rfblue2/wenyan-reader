from pydantic import BaseModel, Field

from wenyan_models.artifacts.base import (
    DEFAULT_ARTIFACT_CONFIG,
    ChapterIdField,
    DocumentIdField,
    ParagraphIdField,
)
from wenyan_models.artifacts.segment import GlossEntry


class ChapterNavItem(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    id: ChapterIdField
    title: str
    path: str


class DocumentManifest(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    schema_version: int = Field(default=1, alias="schemaVersion")
    id: DocumentIdField
    title: str
    gloss_index_path: str = Field(default="glosses/index.json", alias="glossIndexPath")
    chapters: tuple[ChapterNavItem, ...]


class ParagraphNavItem(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    id: ParagraphIdField
    path: str


class ChapterPackage(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    id: ChapterIdField
    title: str
    paragraphs: tuple[ParagraphNavItem, ...]


class GlossIndex(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    glosses: tuple[GlossEntry, ...] = ()
