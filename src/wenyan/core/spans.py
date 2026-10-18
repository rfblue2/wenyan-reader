from collections.abc import Sequence

from wenyan_models.domain.spans import TextSpan
from wenyan_models.domain.validation import CheckResult, ValidationReport


def validate_spans(text_length: int, spans: Sequence[TextSpan]) -> ValidationReport:
    """Check that `spans` tile `[0, text_length)` exactly: no gaps, overlaps, or empty spans."""
    if not spans:
        return ValidationReport.from_checks([CheckResult(code="empty", message="no spans provided")])
    ordered = sorted(spans, key=lambda span: span.start)
    checks: list[CheckResult] = []
    if ordered[0].start != 0:
        checks.append(CheckResult(code="start", message="spans must start at 0"))
    if ordered[-1].end != text_length:
        checks.append(CheckResult(code="end", message="spans must end at text length"))
    for index, span in enumerate(ordered):
        if span.start < 0 or span.end > text_length or span.start >= span.end:
            checks.append(CheckResult(code="bounds", message="invalid span bounds"))
        if index > 0 and span.start != ordered[index - 1].end:
            checks.append(CheckResult(code="gap", message="spans must be contiguous"))
    return ValidationReport.from_checks(checks)
