from collections.abc import Sequence
from typing import Protocol

from wenyan_models.domain.spans import ChapterSpan, ParagraphSpan, SegmentShell
from wenyan_models.domain.validation import SpanValidationResult


class SpanValidator(Protocol):
    def validate_chapters(
        self,
        text_length: int,
        chapters: Sequence[ChapterSpan],
    ) -> SpanValidationResult: ...

    def validate_paragraphs(
        self,
        text_length: int,
        paragraphs: Sequence[ParagraphSpan],
    ) -> SpanValidationResult: ...

    def validate_segments(
        self,
        text_length: int,
        segments: Sequence[SegmentShell],
    ) -> SpanValidationResult: ...
