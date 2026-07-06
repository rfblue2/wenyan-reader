from typing import Annotated, Self

from pydantic import BaseModel, BeforeValidator, model_validator

from wenyan_models.artifacts.base import DEFAULT_ARTIFACT_CONFIG
from wenyan_models.domain.ids import ChapterId, ParagraphId, SegmentId, chapter_id, paragraph_id, segment_id

ChapterIdField = Annotated[ChapterId, BeforeValidator(chapter_id)]
ParagraphIdField = Annotated[ParagraphId, BeforeValidator(paragraph_id)]
SegmentIdField = Annotated[SegmentId, BeforeValidator(segment_id)]


class TextSpan(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    start: int
    end: int

    @model_validator(mode="after")
    def check_bounds(self) -> Self:
        if self.start < 0 or self.end < self.start:
            raise ValueError("invalid span")
        return self


class ChapterSpan(TextSpan):
    id: ChapterIdField
    title: str


class ParagraphSpan(TextSpan):
    id: ParagraphIdField


class SegmentShell(TextSpan):
    id: SegmentIdField
