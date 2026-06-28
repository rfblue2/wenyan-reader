from wenyan_models.artifacts.segment import TokenItem
from wenyan_models.text.tokenization import (
    drop_punctuation_tokens,
    is_punctuation_char,
    is_punctuation_only,
)


def test_is_punctuation_char_recognizes_classical_punctuation() -> None:
    assert is_punctuation_char("，")
    assert is_punctuation_char("。")
    assert is_punctuation_char("：")
    assert not is_punctuation_char("兵")
    assert not is_punctuation_char("曰")


def test_is_punctuation_only() -> None:
    assert is_punctuation_only("，")
    assert is_punctuation_only("。：")
    assert not is_punctuation_only("兵者")
    assert not is_punctuation_only("，兵")


def test_drop_punctuation_tokens() -> None:
    tokens = (
        TokenItem(id="a", surface="兵", start=0, end=1),
        TokenItem(id="b", surface="，", start=1, end=2),
        TokenItem(id="c", surface="者", start=2, end=3),
    )
    filtered = drop_punctuation_tokens(tokens)
    assert len(filtered) == 2
    assert filtered[0].surface == "兵"
    assert filtered[1].surface == "者"
