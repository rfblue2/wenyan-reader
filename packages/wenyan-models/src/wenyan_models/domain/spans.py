from typing import Self

from pydantic import BaseModel, model_validator

from wenyan_models.base import DEFAULT_ARTIFACT_CONFIG
from wenyan_models.domain.ids import ChapterIdField, ParagraphIdField, SegmentIdField


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
