
from wenyan.core.adapters.pure_span_validator import PureSpanValidator
from wenyan_models.domain.enums import ValidationStatus
from wenyan_models.domain.ids import chapter_id, paragraph_id, segment_id
from wenyan_models.domain.spans import ChapterSpan, ParagraphSpan, SegmentShell


def test_ordered_spans_pass() -> None:
    text = "abcdef"
    validator = PureSpanValidator()
    result = validator.validate_chapters(
        text,
        [
            ChapterSpan(id=chapter_id("c1"), title="one", start=0, end=3),
            ChapterSpan(id=chapter_id("c2"), title="two", start=3, end=6),
        ],
    )
    assert result.status == ValidationStatus.PASSED


def test_gap_fails() -> None:
    text = "abcdef"
    validator = PureSpanValidator()
    result = validator.validate_paragraphs(
        text,
        [ParagraphSpan(id=paragraph_id("p1"), start=0, end=2), ParagraphSpan(id=paragraph_id("p2"), start=3, end=6)],
    )
    assert result.status == ValidationStatus.FAILED
    assert result.checks


def test_overlap_fails() -> None:
    text = "abcdef"
    validator = PureSpanValidator()
    result = validator.validate_segments(
        text,
        [
            SegmentShell(id=segment_id("s1"), start=0, end=4),
            SegmentShell(id=segment_id("s2"), start=3, end=6),
        ],
    )
    assert result.status == ValidationStatus.FAILED
