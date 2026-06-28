from collections.abc import Sequence
from typing import Protocol

from wenyan_models.domain.spans import ChapterSpan, ParagraphSpan, SegmentShell
from wenyan_models.domain.validation import SpanValidationResult


class SpanValidator(Protocol):
    def validate_chapters(
        self,
        text: str,
        chapters: Sequence[ChapterSpan],
    ) -> SpanValidationResult: ...

    def validate_paragraphs(
        self,
        text: str,
        paragraphs: Sequence[ParagraphSpan],
    ) -> SpanValidationResult: ...

    def validate_segments(
        self,
        text: str,
        segments: Sequence[SegmentShell],
    ) -> SpanValidationResult: ...
