from collections.abc import Sequence
from typing import Protocol

from wenyan_models.domain.spans import ParagraphSpan
from wenyan_models.domain.validation import SpanValidationResult


class SpanValidator(Protocol):
    def validate_paragraphs(
        self,
        text_length: int,
        paragraphs: Sequence[ParagraphSpan],
    ) -> SpanValidationResult: ...
