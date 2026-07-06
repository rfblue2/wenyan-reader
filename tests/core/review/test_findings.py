from wenyan_models.domain.review import ReviewFinding


def test_review_finding_display_line_uses_message() -> None:
    line = ReviewFinding.model_validate({"message": "Wrong sense for 之."}).display_line()
    assert line == "Wrong sense for 之."


def test_review_finding_display_line_uses_reason_for_context() -> None:
    line = ReviewFinding.model_validate(
        {
            "noteId": "a3b7c4d5-e6f8-4091-b2c3-d4e5f6a7b8c9",
            "reason": "Biographical claims lack source grounding.",
        },
    ).display_line()
    assert "note a3b7c4d5" in line
    assert "Biographical claims lack source grounding." in line


def test_review_finding_display_line_uses_problem_and_detail_for_gloss() -> None:
    line = ReviewFinding.model_validate(
        {
            "surface": "，",
            "problem": "pinyin does not match surface character",
            "detail": "Punctuation should not get a phonetic reading.",
        },
    ).display_line()
    assert "，" in line
    assert "pinyin does not match" in line
    assert "Punctuation should not" in line
