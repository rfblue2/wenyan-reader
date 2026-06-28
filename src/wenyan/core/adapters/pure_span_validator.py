from collections.abc import Sequence

from wenyan.core.ports.span_validator import SpanValidator
from wenyan_models.domain.enums import ValidationStatus
from wenyan_models.domain.spans import ChapterSpan, ParagraphSpan, SegmentShell, TextSpan
from wenyan_models.domain.validation import CheckResult, SpanValidationResult


class PureSpanValidator(SpanValidator):
    def validate_chapters(
        self,
        text: str,
        chapters: Sequence[ChapterSpan],
    ) -> SpanValidationResult:
        return _validate_spans(text, chapters)

    def validate_paragraphs(
        self,
        text: str,
        paragraphs: Sequence[ParagraphSpan],
    ) -> SpanValidationResult:
        return _validate_spans(text, paragraphs)

    def validate_segments(
        self,
        text: str,
        segments: Sequence[SegmentShell],
    ) -> SpanValidationResult:
        return _validate_spans(text, segments)


def _validate_spans(text: str, spans: Sequence[TextSpan]) -> SpanValidationResult:
    if not spans:
        return SpanValidationResult(
            status=ValidationStatus.FAILED,
            checks=(CheckResult(code="empty", message="no spans provided"),),
        )
    ordered = sorted(spans, key=lambda span: span.start)
    checks: list[CheckResult] = []
    if ordered[0].start != 0:
        checks.append(CheckResult(code="start", message="spans must start at 0"))
    if ordered[-1].end != len(text):
        checks.append(CheckResult(code="end", message="spans must end at text length"))
    for index, span in enumerate(ordered):
        if span.start < 0 or span.end > len(text) or span.start >= span.end:
            checks.append(CheckResult(code="bounds", message="invalid span bounds"))
        if index > 0 and span.start != ordered[index - 1].end:
            checks.append(CheckResult(code="gap", message="spans must be contiguous"))
    if checks:
        return SpanValidationResult(status=ValidationStatus.FAILED, checks=tuple(checks))
    reconstructed = "".join(text[span.start : span.end] for span in ordered)
    if reconstructed != text:
        checks.append(CheckResult(code="reconstruct", message="spans do not reconstruct text"))
        return SpanValidationResult(status=ValidationStatus.FAILED, checks=tuple(checks))
    return SpanValidationResult(status=ValidationStatus.PASSED)
