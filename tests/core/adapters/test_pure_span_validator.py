
from wenyan.core.adapters.pure_span_validator import PureSpanValidator
from wenyan_models.domain.enums import ValidationStatus
from wenyan_models.domain.ids import paragraph_id
from wenyan_models.domain.spans import ParagraphSpan


def test_ordered_spans_pass() -> None:
    validator = PureSpanValidator()
    result = validator.validate_paragraphs(
        6,
        [
            ParagraphSpan(id=paragraph_id("p1"), start=0, end=3),
            ParagraphSpan(id=paragraph_id("p2"), start=3, end=6),
        ],
    )
    assert result.status == ValidationStatus.PASSED


def test_gap_fails() -> None:
    validator = PureSpanValidator()
    result = validator.validate_paragraphs(
        6,
        [ParagraphSpan(id=paragraph_id("p1"), start=0, end=2), ParagraphSpan(id=paragraph_id("p2"), start=3, end=6)],
    )
    assert result.status == ValidationStatus.FAILED
    assert result.checks


def test_overlap_fails() -> None:
    validator = PureSpanValidator()
    result = validator.validate_paragraphs(
        6,
        [
            ParagraphSpan(id=paragraph_id("p1"), start=0, end=4),
            ParagraphSpan(id=paragraph_id("p2"), start=3, end=6),
        ],
    )
    assert result.status == ValidationStatus.FAILED
