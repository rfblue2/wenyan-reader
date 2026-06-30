from typing import Literal

from pydantic import BaseModel, Field

from wenyan_models.artifacts.base import DEFAULT_ARTIFACT_CONFIG, ParagraphIdField, SegmentIdField


class ReaderToken(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    id: str
    surface: str
    start: int
    end: int
    gloss_id: str = Field(alias="glossId")


class ReaderNoteSource(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    label: str
    detail: str = ""


class ReaderNote(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    id: str
    type: Literal["grammar", "context"]
    anchor_token_ids: tuple[str, ...] = Field(alias="anchorTokenIds")
    body: str
    sources: tuple[ReaderNoteSource, ...] = ()


class ReaderSegment(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    id: SegmentIdField
    text: str
    new_gloss_ids: tuple[str, ...] = Field(alias="newGlossIds")
    tokens: tuple[ReaderToken, ...]
    notes: tuple[ReaderNote, ...] = ()


class ParagraphPackage(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    id: ParagraphIdField
    segments: tuple[ReaderSegment, ...]
