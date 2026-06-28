from pydantic import BaseModel, ConfigDict

from wenyan.core.ports.artifact_ref import (
    chapter_proposal_ref,
    paragraph_draft_ref,
    paragraph_proposal_ref,
    segment_input_ref,
)
from wenyan.core.ports.artifact_store import ArtifactStore
from wenyan.core.run.segment_pipeline import segment_is_complete
from wenyan_models.artifacts.paragraph import ParagraphDraft
from wenyan_models.artifacts.segment import SegmentInput
from wenyan_models.artifacts.structure import ChapterProposal, ParagraphProposal
from wenyan_models.domain.ids import ChapterId, DocumentId, ParagraphId, SegmentId


_DEFAULT_MODEL_CONFIG = {"frozen": True, "populate_by_name": True, "extra": "forbid"}


class SegmentWorkUnit(BaseModel):
    model_config = ConfigDict(**_DEFAULT_MODEL_CONFIG)

    chapter_id: ChapterId
    paragraph_id: ParagraphId
    segment_id: SegmentId | None = None
    text_preview: str = ""


class ParagraphWorkUnit(BaseModel):
    model_config = ConfigDict(**_DEFAULT_MODEL_CONFIG)

    chapter_id: ChapterId
    paragraph_id: ParagraphId
    text_preview: str = ""


def find_next_paragraph_needing_split_segments(
    artifacts: ArtifactStore,
    document_id: DocumentId,
) -> ParagraphWorkUnit | None:
    for chapter, paragraph in _iter_paragraphs(artifacts, document_id):
        draft_ref = paragraph_draft_ref(document_id, paragraph.id)
        if artifacts.exists(draft_ref):
            continue
        return ParagraphWorkUnit(
            chapter_id=chapter.id,
            paragraph_id=paragraph.id,
            text_preview=_paragraph_preview(artifacts, document_id, chapter.id, paragraph.id),
        )
    return None


def find_next_segment_work(
    artifacts: ArtifactStore,
    document_id: DocumentId,
) -> SegmentWorkUnit | None:
    for chapter, paragraph in _iter_paragraphs(artifacts, document_id):
        draft_ref = paragraph_draft_ref(document_id, paragraph.id)
        if not artifacts.exists(draft_ref):
            return SegmentWorkUnit(
                chapter_id=chapter.id,
                paragraph_id=paragraph.id,
                text_preview=_paragraph_preview(
                    artifacts,
                    document_id,
                    chapter.id,
                    paragraph.id,
                ),
            )
        draft = artifacts.read(draft_ref, ParagraphDraft)
        for segment in draft.segments:
            if segment_is_complete(artifacts, document_id, segment.id):
                continue
            preview = _segment_preview(artifacts, document_id, segment.id, segment.text)
            return SegmentWorkUnit(
                chapter_id=chapter.id,
                paragraph_id=paragraph.id,
                segment_id=segment.id,
                text_preview=preview,
            )
    return None


def _iter_paragraphs(
    artifacts: ArtifactStore,
    document_id: DocumentId,
):
    if not artifacts.exists(chapter_proposal_ref(document_id)):
        return
    chapter_proposal = artifacts.read(chapter_proposal_ref(document_id), ChapterProposal)
    for chapter in chapter_proposal.chapters:
        proposal_ref = paragraph_proposal_ref(document_id, chapter.id)
        if not artifacts.exists(proposal_ref):
            continue
        paragraph_proposal = artifacts.read(proposal_ref, ParagraphProposal)
        for paragraph in paragraph_proposal.paragraphs:
            yield chapter, paragraph


def _paragraph_preview(
    artifacts: ArtifactStore,
    document_id: DocumentId,
    chapter_id: ChapterId,
    paragraph_id: ParagraphId,
) -> str:
    draft_ref = paragraph_draft_ref(document_id, paragraph_id)
    if artifacts.exists(draft_ref):
        draft = artifacts.read(draft_ref, ParagraphDraft)
        if draft.segments:
            return _preview_text(draft.segments[0].text)
    proposal_ref = paragraph_proposal_ref(document_id, chapter_id)
    if artifacts.exists(proposal_ref):
        proposal = artifacts.read(proposal_ref, ParagraphProposal)
        for paragraph in proposal.paragraphs:
            if paragraph.id == paragraph_id:
                return f"paragraph@{paragraph.start}:{paragraph.end}"
    return ""


def _segment_preview(
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


def _preview_text(text: str, *, limit: int = 40) -> str:
    compact = text.replace("\n", " ").strip()
    if len(compact) <= limit:
        return compact
    return f"{compact[: limit - 1]}…"
