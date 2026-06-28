from typing import Literal

from pydantic import BaseModel, Field

from wenyan_models.artifacts.base import DEFAULT_ARTIFACT_CONFIG


class StatusCounts(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    chapters: int | None = None
    paragraphs: int | None = None
    segments: int | None = None
    complete: int = 0
    in_progress: int = Field(default=0, alias="inProgress")
    pending: int = 0
    failed: int = 0
    blocked: int = 0


class ChapterProgress(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    paragraphs_complete: int = Field(alias="paragraphsComplete")
    paragraphs_total: int | None = Field(alias="paragraphsTotal")


class ParagraphProgress(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    segments_complete: int = Field(alias="segmentsComplete")
    segments_total: int | None = Field(alias="segmentsTotal")


class SegmentProgress(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    components_complete: int = Field(alias="componentsComplete")
    components_total: int = Field(alias="componentsTotal")


class ScopeDocument(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    type: Literal["document"] = "document"


class ScopeChapter(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    type: Literal["chapter"] = "chapter"


class ScopeParagraph(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    type: Literal["paragraph"] = "paragraph"


class ScopeSegment(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    type: Literal["segment"] = "segment"
