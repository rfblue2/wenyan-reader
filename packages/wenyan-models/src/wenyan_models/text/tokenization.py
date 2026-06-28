import unicodedata

from wenyan_models.artifacts.segment import TokenItem


def is_punctuation_char(character: str) -> bool:
    if len(character) != 1:
        return False
    if character.isspace():
        return True
    return unicodedata.category(character).startswith("P")


def is_punctuation_only(text: str) -> bool:
    return bool(text) and all(is_punctuation_char(character) for character in text)


def drop_punctuation_tokens(tokens: tuple[TokenItem, ...]) -> tuple[TokenItem, ...]:
    return tuple(token for token in tokens if not is_punctuation_only(token.surface))
