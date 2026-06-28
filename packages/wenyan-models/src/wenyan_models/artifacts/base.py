from typing import Annotated

from pydantic import BeforeValidator, ConfigDict

from wenyan_models.domain.ids import (
    ChapterId,
    ContentHash,
    DocumentId,
    ParagraphId,
    PromptVersion,
    SegmentId,
    chapter_id,
    document_id,
    paragraph_id,
    parse_content_hash,
    prompt_version,
    segment_id,
)

DEFAULT_ARTIFACT_CONFIG = ConfigDict(frozen=True, populate_by_name=True, extra="forbid")

DocumentIdField = Annotated[DocumentId, BeforeValidator(document_id)]
ChapterIdField = Annotated[ChapterId, BeforeValidator(chapter_id)]
ParagraphIdField = Annotated[ParagraphId, BeforeValidator(paragraph_id)]
SegmentIdField = Annotated[SegmentId, BeforeValidator(segment_id)]
ContentHashField = Annotated[ContentHash, BeforeValidator(parse_content_hash)]
PromptVersionField = Annotated[PromptVersion, BeforeValidator(prompt_version)]
