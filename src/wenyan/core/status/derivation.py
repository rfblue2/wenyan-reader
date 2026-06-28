from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from wenyan.core.adapters.paths import artifact_path
from wenyan.core.ports.artifact_ref import paragraph_draft_ref, paragraph_proposal_ref, segment_input_ref
from wenyan.core.ports.artifact_store import ArtifactStore
from wenyan.core.run.segment_pipeline import (
    SEGMENT_SUBJOBS,
    component_artifact_ref,
    component_unit_status,
    read_review_component,
)
from wenyan.core.run.work_queue import _iter_paragraphs, _preview_text
from wenyan_models.artifacts.paragraph import ParagraphDraft
from wenyan_models.artifacts.segment import SegmentInput
from wenyan_models.artifacts.structure import ParagraphProposal
from wenyan_models.domain.enums import ComponentKind, UnitStatus
from wenyan_models.domain.ids import ChapterId, DocumentId, ParagraphId, SegmentId
from wenyan_models.status.chapter import ChapterStatus, ParagraphStatusItem
from wenyan_models.status.common import StatusCounts
from wenyan_models.status.component import ComponentStatusItem
from wenyan_models.status.document import ChapterStatusItem, DocumentSourceStatus, DocumentStatus
from wenyan_models.status.paragraph import (
    ParagraphStatus,
    ParagraphStructureStatus,
    SegmentStatusItem,
)
from wenyan_models.status.segment import SegmentStatus


@dataclass(frozen=True)
class _SegmentRollup:
    status: UnitStatus
    components_complete: int
    components_total: int
    blocked_component: ComponentKind | None
    components: tuple[ComponentStatusItem, ...]


def derive_document_status(
    artifacts: ArtifactStore,
    repo_root: Path,
    *,
    document_id: DocumentId,
    title: str,
    source: DocumentSourceStatus,
    chapter_items: Iterable[tuple[str, ChapterId]],
) -> DocumentStatus:
    chapters: list[ChapterStatusItem] = []
    statuses: list[UnitStatus] = []
    for chapter_title, chapter_id_value in chapter_items:
        chapter_payload = derive_chapter_status(
            artifacts,
            repo_root,
            document_id=document_id,
            chapter_id=chapter_id_value,
        )
        chapter_status = _rollup_chapter_status(chapter_payload)
        chapters.append(
            ChapterStatusItem.model_validate(
                {
                    "chapterId": str(chapter_id_value),
                    "title": chapter_title,
                    "status": chapter_status.value,
                    "progress": {
                        "paragraphsComplete": chapter_payload.counts.complete,
                        "paragraphsTotal": chapter_payload.counts.paragraphs,
                    },
                },
            ),
        )
        statuses.append(chapter_status)
    return DocumentStatus.model_validate(
        {
            "documentId": str(document_id),
            "title": title,
            "scope": {"type": "document"},
            "source": source.model_dump(by_alias=True),
            "counts": _build_counts(statuses, chapters=len(chapters)).model_dump(by_alias=True),
            "chapters": [chapter.model_dump(by_alias=True) for chapter in chapters],
        },
    )


def derive_chapter_status(
    artifacts: ArtifactStore,
    repo_root: Path,
    *,
    document_id: DocumentId,
    chapter_id: ChapterId,
) -> ChapterStatus:
    paragraphs: list[ParagraphStatusItem] = []
    statuses: list[UnitStatus] = []
    proposal_ref = paragraph_proposal_ref(document_id, chapter_id)
    has_proposal = artifacts.exists(proposal_ref)
    if has_proposal:
        proposal = artifacts.read(proposal_ref, ParagraphProposal)
        for ordinal, paragraph in enumerate(proposal.paragraphs, start=1):
            paragraph_payload = derive_paragraph_status(
                artifacts,
                repo_root,
                document_id=document_id,
                chapter_id=chapter_id,
                paragraph_id=paragraph.id,
            )
            paragraph_status = _rollup_paragraph_status(paragraph_payload)
            paragraphs.append(
                ParagraphStatusItem.model_validate(
                    {
                        "paragraphId": str(paragraph.id),
                        "ordinal": ordinal,
                        "status": paragraph_status.value,
                        "progress": {
                            "segmentsComplete": paragraph_payload.counts.complete,
                            "segmentsTotal": paragraph_payload.counts.segments,
                        },
                    },
                ),
            )
            statuses.append(paragraph_status)
    return ChapterStatus.model_validate(
        {
            "documentId": str(document_id),
            "chapterId": str(chapter_id),
            "scope": {"type": "chapter"},
            "counts": _build_counts(statuses, paragraphs=len(paragraphs) if has_proposal else None).model_dump(
                by_alias=True,
            ),
            "paragraphs": [paragraph.model_dump(by_alias=True) for paragraph in paragraphs],
        },
    )


def derive_paragraph_status(
    artifacts: ArtifactStore,
    repo_root: Path,
    *,
    document_id: DocumentId,
    chapter_id: ChapterId,
    paragraph_id: ParagraphId,
) -> ParagraphStatus:
    draft_ref = paragraph_draft_ref(document_id, paragraph_id)
    has_draft = artifacts.exists(draft_ref)
    structure = ParagraphStructureStatus(
        status=UnitStatus.COMPLETE if has_draft else UnitStatus.PENDING,
        segment_count=None,
    )
    segments: list[SegmentStatusItem] = []
    statuses: list[UnitStatus] = []
    if has_draft:
        draft = artifacts.read(draft_ref, ParagraphDraft)
        structure = structure.model_copy(update={"segment_count": len(draft.segments)})
        for ordinal, segment in enumerate(draft.segments, start=1):
            rollup = _derive_segment_rollup(artifacts, repo_root, document_id, segment.id)
            segments.append(
                SegmentStatusItem.model_validate(
                    {
                        "segmentId": str(segment.id),
                        "ordinal": ordinal,
                        "status": rollup.status.value,
                        "textPreview": _segment_text_preview(
                            artifacts,
                            document_id,
                            segment.id,
                            segment.text,
                        ),
                        "progress": {
                            "componentsComplete": rollup.components_complete,
                            "componentsTotal": rollup.components_total,
                        },
                        "blockedComponent": rollup.blocked_component.value if rollup.blocked_component else None,
                    },
                ),
            )
            statuses.append(rollup.status)
    return ParagraphStatus.model_validate(
        {
            "documentId": str(document_id),
            "chapterId": str(chapter_id),
            "paragraphId": str(paragraph_id),
            "scope": {"type": "paragraph"},
            "structure": {
                "status": structure.status.value,
                "segmentCount": structure.segment_count,
            },
            "counts": _build_counts(statuses, segments=len(segments)).model_dump(by_alias=True),
            "segments": [segment.model_dump(by_alias=True) for segment in segments],
        },
    )


def derive_segment_status(
    artifacts: ArtifactStore,
    repo_root: Path,
    *,
    document_id: DocumentId,
    chapter_id: ChapterId,
    paragraph_id: ParagraphId,
    segment_id: SegmentId,
    text: str,
) -> SegmentStatus:
    rollup = _derive_segment_rollup(artifacts, repo_root, document_id, segment_id)
    return SegmentStatus.model_validate(
        {
            "documentId": str(document_id),
            "chapterId": str(chapter_id),
            "paragraphId": str(paragraph_id),
            "segmentId": str(segment_id),
            "scope": {"type": "segment"},
            "text": text,
            "status": rollup.status.value,
            "components": [component.model_dump(by_alias=True) for component in rollup.components],
        },
    )


def find_paragraph_chapter(
    artifacts: ArtifactStore,
    document_id: DocumentId,
    paragraph_id: ParagraphId,
) -> ChapterId | None:
    for chapter, paragraph in _iter_paragraphs(artifacts, document_id):
        if paragraph.id == paragraph_id:
            return ChapterId(str(chapter.id))
    return None


def find_segment_location(
    artifacts: ArtifactStore,
    document_id: DocumentId,
    segment_id: SegmentId,
) -> tuple[ChapterId, ParagraphId, str] | None:
    input_ref = segment_input_ref(document_id, segment_id)
    if artifacts.exists(input_ref):
        segment_input = artifacts.read(input_ref, SegmentInput)
        return segment_input.chapter_id, segment_input.paragraph_id, segment_input.segment_text
    for chapter, paragraph in _iter_paragraphs(artifacts, document_id):
        draft_ref = paragraph_draft_ref(document_id, paragraph.id)
        if not artifacts.exists(draft_ref):
            continue
        draft = artifacts.read(draft_ref, ParagraphDraft)
        for segment in draft.segments:
            if segment.id == segment_id:
                return chapter.id, paragraph.id, segment.text
    return None


def _derive_segment_rollup(
    artifacts: ArtifactStore,
    repo_root: Path,
    document_id: DocumentId,
    segment_id: SegmentId,
) -> _SegmentRollup:
    components: list[ComponentStatusItem] = []
    components_complete = 0
    blocked_component: ComponentKind | None = None
    for component in SEGMENT_SUBJOBS:
        status = component_unit_status(artifacts, document_id, segment_id, component)
        components.append(_component_status_item(artifacts, repo_root, document_id, segment_id, component, status))
        if status == UnitStatus.COMPLETE:
            components_complete += 1
        elif status == UnitStatus.BLOCKED and blocked_component is None:
            blocked_component = component
    if blocked_component is not None:
        overall = UnitStatus.BLOCKED
    elif components_complete == len(SEGMENT_SUBJOBS):
        overall = UnitStatus.COMPLETE
    elif components_complete == 0:
        overall = UnitStatus.PENDING
    else:
        overall = UnitStatus.IN_PROGRESS
    return _SegmentRollup(
        status=overall,
        components_complete=components_complete,
        components_total=len(SEGMENT_SUBJOBS),
        blocked_component=blocked_component,
        components=tuple(components),
    )


def _component_status_item(
    artifacts: ArtifactStore,
    repo_root: Path,
    document_id: DocumentId,
    segment_id: SegmentId,
    component: ComponentKind,
    status: UnitStatus,
) -> ComponentStatusItem:
    ref = component_artifact_ref(document_id, segment_id, component)
    artifact_path_value = (
        artifact_path(repo_root, ref).relative_to(repo_root).as_posix() if ref and artifacts.exists(ref) else None
    )
    if status != UnitStatus.BLOCKED:
        review = read_review_component(artifacts, document_id, segment_id, component)
        attempts = review.attempts if review is not None else None
        return ComponentStatusItem.model_validate(
            {
                "kind": component.value,
                "status": status.value,
                "artifactPath": artifact_path_value,
                "attempts": attempts,
            },
        )
    review = read_review_component(artifacts, document_id, segment_id, component)
    blocked_reason = None
    required_fixes: tuple[dict[str, object], ...] = ()
    attempts = None
    if review is not None:
        attempts = review.attempts
        required_fixes = review.findings
        blocked_reason = _blocked_reason(review.findings)
    return ComponentStatusItem.model_validate(
        {
            "kind": component.value,
            "status": status.value,
            "artifactPath": artifact_path_value,
            "attempts": attempts,
            "blockedReason": blocked_reason,
            "requiredFixes": list(required_fixes),
        },
    )


def _blocked_reason(findings: tuple[dict[str, object], ...]) -> str | None:
    for finding in findings:
        message = finding.get("message")
        if isinstance(message, str) and message:
            return message
    return None


def _segment_text_preview(
    artifacts: ArtifactStore,
    document_id: DocumentId,
    segment_id: SegmentId,
    fallback_text: str,
) -> str:
    input_ref = segment_input_ref(document_id, segment_id)
    if artifacts.exists(input_ref):
        segment_input = artifacts.read(input_ref, SegmentInput)
        return _preview_text(segment_input.segment_text)
    return _preview_text(fallback_text)


def _build_counts(
    statuses: Iterable[UnitStatus],
    *,
    chapters: int | None = None,
    paragraphs: int | None = None,
    segments: int | None = None,
) -> StatusCounts:
    complete = in_progress = pending = failed = blocked = 0
    for status in statuses:
        match status:
            case UnitStatus.COMPLETE:
                complete += 1
            case UnitStatus.IN_PROGRESS:
                in_progress += 1
            case UnitStatus.PENDING | UnitStatus.STALE:
                pending += 1
            case UnitStatus.FAILED:
                failed += 1
            case UnitStatus.BLOCKED:
                blocked += 1
    return StatusCounts.model_validate(
        {
            "chapters": chapters,
            "paragraphs": paragraphs,
            "segments": segments,
            "complete": complete,
            "inProgress": in_progress,
            "pending": pending,
            "failed": failed,
            "blocked": blocked,
        },
    )


def _rollup_chapter_status(chapter: ChapterStatus) -> UnitStatus:
    if chapter.counts.blocked:
        return UnitStatus.BLOCKED
    if chapter.counts.paragraphs and chapter.counts.complete == chapter.counts.paragraphs:
        return UnitStatus.COMPLETE
    if chapter.counts.complete > 0 or chapter.counts.in_progress > 0:
        return UnitStatus.IN_PROGRESS
    return UnitStatus.PENDING


def _rollup_paragraph_status(paragraph: ParagraphStatus) -> UnitStatus:
    if paragraph.counts.blocked:
        return UnitStatus.BLOCKED
    if paragraph.counts.segments and paragraph.counts.complete == paragraph.counts.segments:
        return UnitStatus.COMPLETE
    if paragraph.structure.status != UnitStatus.COMPLETE:
        return UnitStatus.PENDING
    if paragraph.counts.complete or paragraph.counts.in_progress or paragraph.counts.blocked:
        return UnitStatus.IN_PROGRESS
    return UnitStatus.PENDING
