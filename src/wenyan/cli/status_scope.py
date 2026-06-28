from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Literal

from wenyan.core.ports.artifact_ref import chapter_proposal_ref, paragraph_draft_ref, paragraph_proposal_ref
from wenyan.core.ports.artifact_store import ArtifactStore
from wenyan.core.status.derivation import find_paragraph_chapter
from wenyan_models.artifacts.paragraph import ParagraphDraft
from wenyan_models.artifacts.structure import ChapterProposal, ParagraphProposal
from wenyan_models.domain.ids import ChapterId, DocumentId, ParagraphId, SegmentId, chapter_id, paragraph_id, segment_id


@dataclass(frozen=True)
class StatusScope:
    document_ref: str
    chapter_id: ChapterId | None = None
    chapter_handle: str | None = None
    paragraph_id: ParagraphId | None = None
    paragraph_handle: str | None = None
    segment_id: SegmentId | None = None
    segment_handle: str | None = None

    @property
    def level(self) -> Literal["document", "chapter", "paragraph", "segment"]:
        if self.segment_id is not None:
            return "segment"
        if self.paragraph_id is not None:
            return "paragraph"
        if self.chapter_id is not None:
            return "chapter"
        return "document"


def resolve_status_scope(
    artifacts: ArtifactStore,
    document_id: DocumentId,
    document_ref: str,
    *,
    chapter: str | None,
    paragraph: str | None,
    segment: str | None,
) -> StatusScope:
    scope = StatusScope(document_ref=document_ref)
    if chapter is not None:
        chapter_id_value, chapter_handle = _resolve_chapter_ref(artifacts, document_id, chapter)
        scope = StatusScope(
            document_ref=document_ref,
            chapter_id=chapter_id_value,
            chapter_handle=chapter_handle,
        )
    if paragraph is not None:
        if scope.chapter_id is None:
            paragraph_id_value, paragraph_handle = _resolve_paragraph_ref_by_uuid(document_id, paragraph)
        else:
            paragraph_id_value, paragraph_handle = _resolve_paragraph_ref(
                artifacts,
                document_id,
                scope.chapter_id,
                paragraph,
            )
        scope = StatusScope(
            document_ref=document_ref,
            chapter_id=scope.chapter_id,
            chapter_handle=scope.chapter_handle,
            paragraph_id=paragraph_id_value,
            paragraph_handle=paragraph_handle,
        )
    if segment is not None:
        segment_id_value, segment_handle = _resolve_segment_ref(
            artifacts,
            document_id,
            segment,
            chapter_id=scope.chapter_id,
            paragraph_id=scope.paragraph_id,
        )
        scope = StatusScope(
            document_ref=document_ref,
            chapter_id=scope.chapter_id,
            chapter_handle=scope.chapter_handle,
            paragraph_id=scope.paragraph_id,
            paragraph_handle=scope.paragraph_handle,
            segment_id=segment_id_value,
            segment_handle=segment_handle,
        )
    return scope


def build_display_context(
    artifacts: ArtifactStore,
    document_id: DocumentId,
    scope: StatusScope,
) -> tuple[str | None, str | None]:
    chapter_handle = scope.chapter_handle
    paragraph_handle = scope.paragraph_handle
    chapter_id_value = scope.chapter_id
    if chapter_id_value is None and scope.paragraph_id is not None:
        chapter_id_value = find_paragraph_chapter(artifacts, document_id, scope.paragraph_id)
    if chapter_id_value is not None and chapter_handle is None:
        chapter_handle = _chapter_handle_for_id(artifacts, document_id, chapter_id_value)
    if scope.paragraph_id is not None and chapter_id_value is not None and paragraph_handle is None:
        paragraph_handle = _paragraph_handle_for_id(
            artifacts,
            document_id,
            chapter_id_value,
            scope.paragraph_id,
        )
    if scope.segment_id is not None and scope.paragraph_id is not None and paragraph_handle is None:
        paragraph_handle = _paragraph_handle_for_id(
            artifacts,
            document_id,
            chapter_id_value,
            scope.paragraph_id,
        ) if chapter_id_value else None
    return chapter_handle, paragraph_handle


def _chapter_handle_for_id(
    artifacts: ArtifactStore,
    document_id: DocumentId,
    chapter_id_value: ChapterId,
) -> str:
    proposal = _load_chapter_proposal(artifacts, document_id)
    for ordinal, chapter in enumerate(proposal.chapters, start=1):
        if chapter.id == chapter_id_value:
            return str(ordinal)
    return str(chapter_id_value)


def _paragraph_handle_for_id(
    artifacts: ArtifactStore,
    document_id: DocumentId,
    chapter_id_value: ChapterId,
    paragraph_id_value: ParagraphId,
) -> str:
    proposal = _load_paragraph_proposal(artifacts, document_id, chapter_id_value)
    for ordinal, paragraph in enumerate(proposal.paragraphs, start=1):
        if paragraph.id == paragraph_id_value:
            return str(ordinal)
    return str(paragraph_id_value)


def _resolve_chapter_ref(
    artifacts: ArtifactStore,
    document_id: DocumentId,
    ref: str,
) -> tuple[ChapterId, str]:
    proposal = _load_chapter_proposal(artifacts, document_id)
    if _is_uuid(ref):
        chapter_id_value = chapter_id(ref)
        for chapter_ordinal, chapter in enumerate(proposal.chapters, start=1):
            if chapter.id == chapter_id_value:
                return chapter_id_value, str(chapter_ordinal)
        raise ValueError(f"chapter {ref} was not found in document {document_id}")
    chapter_number = _parse_ordinal(ref)
    if chapter_number is not None:
        if chapter_number < 1 or chapter_number > len(proposal.chapters):
            raise ValueError(f"chapter #{chapter_number} is out of range (1-{len(proposal.chapters)})")
        chapter = proposal.chapters[chapter_number - 1]
        return ChapterId(str(chapter.id)), str(chapter_number)
    matches = [chapter for chapter in proposal.chapters if chapter.title == ref]
    if len(matches) == 1:
        return ChapterId(str(matches[0].id)), ref
    prefix_matches = [chapter for chapter in proposal.chapters if chapter.title.startswith(ref)]
    if len(prefix_matches) == 1:
        return ChapterId(str(prefix_matches[0].id)), prefix_matches[0].title
    if len(matches) > 1 or len(prefix_matches) > 1:
        raise ValueError(f"chapter title {ref!r} is ambiguous")
    raise ValueError(f"chapter {ref!r} was not found in document {document_id}")


def _resolve_paragraph_ref_by_uuid(
    document_id: DocumentId,
    ref: str,
) -> tuple[ParagraphId, str]:
    if not _is_uuid(ref):
        raise ValueError("paragraph number requires --chapter; use a paragraph UUID or add --chapter")
    return paragraph_id(ref), ref


def _resolve_paragraph_ref(
    artifacts: ArtifactStore,
    document_id: DocumentId,
    chapter_id_value: ChapterId,
    ref: str,
) -> tuple[ParagraphId, str]:
    proposal = _load_paragraph_proposal(artifacts, document_id, chapter_id_value)
    if _is_uuid(ref):
        paragraph_id_value = paragraph_id(ref)
        for paragraph_ordinal, paragraph in enumerate(proposal.paragraphs, start=1):
            if paragraph.id == paragraph_id_value:
                return paragraph_id_value, str(paragraph_ordinal)
        raise ValueError(f"paragraph {ref} was not found in chapter {chapter_id_value}")
    paragraph_number = _parse_ordinal(ref)
    if paragraph_number is None:
        raise ValueError(f"paragraph {ref!r} must be a UUID or a number when --chapter is set")
    if paragraph_number < 1 or paragraph_number > len(proposal.paragraphs):
        raise ValueError(f"paragraph #{paragraph_number} is out of range (1-{len(proposal.paragraphs)})")
    paragraph = proposal.paragraphs[paragraph_number - 1]
    return ParagraphId(str(paragraph.id)), str(paragraph_number)


def _resolve_segment_ref(
    artifacts: ArtifactStore,
    document_id: DocumentId,
    ref: str,
    *,
    chapter_id: ChapterId | None,
    paragraph_id: ParagraphId | None,
) -> tuple[SegmentId, str]:
    if _is_uuid(ref):
        return segment_id(ref), ref
    segment_number = _parse_ordinal(ref)
    if segment_number is None:
        raise ValueError(f"segment {ref!r} must be a UUID or a number when --paragraph is set")
    if paragraph_id is None:
        raise ValueError("segment number requires --paragraph; use a segment UUID or add --paragraph")
    draft_ref = paragraph_draft_ref(document_id, paragraph_id)
    if not artifacts.exists(draft_ref):
        raise ValueError(f"paragraph {paragraph_id} has no segment draft yet")
    draft = artifacts.read(draft_ref, ParagraphDraft)
    if segment_number < 1 or segment_number > len(draft.segments):
        raise ValueError(f"segment #{segment_number} is out of range (1-{len(draft.segments)})")
    segment = draft.segments[segment_number - 1]
    return SegmentId(str(segment.id)), str(segment_number)


def _load_chapter_proposal(artifacts: ArtifactStore, document_id: DocumentId) -> ChapterProposal:
    ref = chapter_proposal_ref(document_id)
    if not artifacts.exists(ref):
        raise ValueError("document has no chapter structure yet")
    return artifacts.read(ref, ChapterProposal)


def _load_paragraph_proposal(
    artifacts: ArtifactStore,
    document_id: DocumentId,
    chapter_id_value: ChapterId,
) -> ParagraphProposal:
    ref = paragraph_proposal_ref(document_id, chapter_id_value)
    if not artifacts.exists(ref):
        raise ValueError(f"chapter {chapter_id_value} has no paragraph structure yet")
    return artifacts.read(ref, ParagraphProposal)


def _is_uuid(value: str) -> bool:
    try:
        uuid.UUID(value)
    except ValueError:
        return False
    return True


def _parse_ordinal(value: str) -> int | None:
    if not value.isdigit():
        return None
    ordinal = int(value)
    if ordinal < 1:
        return None
    return ordinal
