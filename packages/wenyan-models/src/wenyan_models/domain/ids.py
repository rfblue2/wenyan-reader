from typing import NewType

DocumentId = NewType("DocumentId", str)
ChapterId = NewType("ChapterId", str)
ParagraphId = NewType("ParagraphId", str)
SegmentId = NewType("SegmentId", str)
Slug = NewType("Slug", str)
ContentHash = NewType("ContentHash", str)


def document_id(value: str) -> DocumentId:
    if not value.strip():
        raise ValueError("document id must be non-empty")
    return DocumentId(value)


def chapter_id(value: str) -> ChapterId:
    if not value.strip():
        raise ValueError("chapter id must be non-empty")
    return ChapterId(value)


def paragraph_id(value: str) -> ParagraphId:
    if not value.strip():
        raise ValueError("paragraph id must be non-empty")
    return ParagraphId(value)


def segment_id(value: str) -> SegmentId:
    if not value.strip():
        raise ValueError("segment id must be non-empty")
    return SegmentId(value)


def slug(value: str) -> Slug:
    if not value.strip():
        raise ValueError("slug must be non-empty")
    return Slug(value)


def parse_content_hash(value: str) -> ContentHash:
    if not value.startswith("sha256:"):
        raise ValueError("content hash must start with sha256:")
    return ContentHash(value)
