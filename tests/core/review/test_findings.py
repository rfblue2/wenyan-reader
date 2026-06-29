from wenyan.core.review.findings import format_review_finding


def test_format_review_finding_uses_message() -> None:
    line = format_review_finding({"message": "Wrong sense for 之."})
    assert line == "Wrong sense for 之."


def test_format_review_finding_uses_reason_for_context() -> None:
    line = format_review_finding(
        {
            "noteId": "a3b7c4d5-e6f8-4091-b2c3-d4e5f6a7b8c9",
            "reason": "Biographical claims lack source grounding.",
        },
    )
    assert "note a3b7c4d5" in line
    assert "Biographical claims lack source grounding." in line


def test_format_review_finding_uses_problem_and_detail_for_gloss() -> None:
    line = format_review_finding(
        {
            "surface": "，",
            "problem": "pinyin does not match surface character",
            "detail": "Punctuation should not get a phonetic reading.",
        },
    )
    assert "，" in line
    assert "pinyin does not match" in line
    assert "Punctuation should not" in line
