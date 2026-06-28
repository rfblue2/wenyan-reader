import pytest

from wenyan_models.domain.ids import (
    ContentHash,
    document_id,
    parse_content_hash,
)


def test_document_id_wraps_value() -> None:
    value = document_id("9ad841a6-f20f-4f43-9805-166ab2d98e7f")
    assert value == "9ad841a6-f20f-4f43-9805-166ab2d98e7f"


def test_document_id_rejects_empty() -> None:
    with pytest.raises(ValueError, match="non-empty"):
        document_id("")


def test_parse_content_hash_requires_prefix() -> None:
    with pytest.raises(ValueError, match="sha256:"):
        parse_content_hash("abc123")


def test_parse_content_hash_accepts_valid() -> None:
    value = parse_content_hash("sha256:deadbeef")
    assert isinstance(value, str)
    assert value == "sha256:deadbeef"
