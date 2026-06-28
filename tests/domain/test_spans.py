import pytest
from pydantic import ValidationError

from wenyan_models.domain.ids import chapter_id
from wenyan_models.domain.spans import ChapterSpan, ParagraphSpan, SegmentShell, TextSpan


def test_text_span_rejects_invalid_bounds() -> None:
    with pytest.raises(ValidationError):
        TextSpan(start=5, end=3)


def test_chapter_span_rejects_invalid_bounds() -> None:
    with pytest.raises(ValidationError):
        ChapterSpan(id=chapter_id("ch-1"), title="卷一", start=5, end=3)


def test_paragraph_span_accepts_valid_bounds() -> None:
    span = ParagraphSpan(id="p-1", start=0, end=10)
    assert span.start == 0
    assert span.end == 10


def test_segment_shell_accepts_valid_bounds() -> None:
    shell = SegmentShell(id="s-1", start=0, end=5)
    assert shell.end == 5
