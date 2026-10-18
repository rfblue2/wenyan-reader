from wenyan.core.hashing import sha256_text
from wenyan.core.ports.artifact_ref import (
    ChapterArtifactKind,
    ChapterRef,
    DocumentArtifactKind,
    DocumentRef,
    ParagraphArtifactKind,
    ParagraphRef,
    SegmentArtifactKind,
    SegmentRef,
)
from wenyan.core.ports.artifact_store import ArtifactWrite
from wenyan.core.ports.prompt_context import PromptTextSlice
from wenyan.jobs.context import JobContext, JobOptions
from wenyan_models.artifacts.paragraph import ParagraphDraft
from wenyan_models.artifacts.segment import SegmentInput
from wenyan_models.artifacts.structure import ChapterProposal, ParagraphProposal
from wenyan_models.domain.ids import DocumentId, ParagraphId, chapter_id, segment_id
from wenyan_models.domain.results import JobFailure, JobOutcome, Promoted, Skipped
from wenyan_models.domain.validation import ValidationReport


def run_split_segments(
    ctx: JobContext,
    document_id: DocumentId,
    paragraph_id_value: ParagraphId,
    options: JobOptions,
) -> JobOutcome[ParagraphDraft]:
    chapter_proposal = ctx.artifacts.read(
        DocumentRef(DocumentArtifactKind.CHAPTER_PROPOSAL, document_id),
        ChapterProposal,
    )
    paragraph_proposal = _find_paragraph_proposal(ctx, document_id, chapter_proposal, paragraph_id_value)
    if paragraph_proposal is None:
        return JobFailure(code="missing-paragraph", message="paragraph proposal not found")
    chapter = next(
        (item for item in chapter_proposal.chapters if item.id == paragraph_proposal.chapter_id),
        None,
    )
    if chapter is None:
        return JobFailure(code="missing-chapter", message="chapter not found")
    paragraph_item = next(
        (item for item in paragraph_proposal.paragraphs if item.id == paragraph_id_value),
        None,
    )
    if paragraph_item is None:
        return JobFailure(code="missing-paragraph", message="paragraph not in proposal")
    paragraph_start = chapter.start + paragraph_item.start
    paragraph_end = chapter.start + paragraph_item.end
    draft_ref = ParagraphRef(ParagraphArtifactKind.DRAFT, document_id, paragraph_id_value)
    paragraph_text = ctx.normalized_text.read_slice(document_id, paragraph_start, paragraph_end)
    input_hash = sha256_text(paragraph_text)
    if ctx.artifacts.exists(draft_ref) and not options.force:
        existing = ctx.artifacts.read(draft_ref, ParagraphDraft)
        if existing.input_hash == input_hash:
            return Skipped(reason="paragraph draft is current")
    context: dict[str, str | PromptTextSlice] = {
        "paragraph_text": PromptTextSlice(document_id, paragraph_start, paragraph_end),
        "paragraph_id": str(paragraph_id_value),
        "input_hash": str(input_hash),
    }
    prompt = ctx.prompts.build_prompt(
        "paragraph-segmentation",
        context,
        normalized_text=ctx.normalized_text,
    )
    draft = ctx.llm.complete_model(
        prompt,
        ParagraphDraft,
    )
    draft = draft.model_copy(
        update={
            "paragraph_id": paragraph_id_value,
            "input_hash": input_hash,
            "model": ctx.config.models.active_model,
            "attempts": 1,
        },
    )
    validation = ValidationReport.from_checks()
    writes: list[ArtifactWrite] = [
        ArtifactWrite(ref=draft_ref, payload=draft),
        ArtifactWrite(
            ref=ParagraphRef(
                ParagraphArtifactKind.DRAFT_VALIDATION,
                document_id,
                paragraph_id_value,
            ),
            payload=validation,
        ),
    ]
    for segment in draft.segments:
        writes.append(
            ArtifactWrite(
                ref=SegmentRef(SegmentArtifactKind.INPUT, document_id, segment_id(str(segment.id))),
                payload=SegmentInput.model_validate(
                    {
                        "documentId": str(document_id),
                        "chapterId": str(paragraph_proposal.chapter_id),
                        "paragraphId": str(paragraph_id_value),
                        "segmentId": str(segment.id),
                        "segmentText": segment.text,
                    },
                ),
            ),
        )
    if options.dry_run:
        return Promoted(artifact=draft)
    ctx.artifacts.write_batch(writes, dry_run=False)
    return Promoted(artifact=draft)


def _find_paragraph_proposal(
    ctx: JobContext,
    document_id: DocumentId,
    chapter_proposal: ChapterProposal,
    paragraph_id_value: ParagraphId,
) -> ParagraphProposal | None:
    for chapter in chapter_proposal.chapters:
        ref = ChapterRef(
            ChapterArtifactKind.PARAGRAPH_PROPOSAL,
            document_id,
            chapter_id(str(chapter.id)),
        )
        if not ctx.artifacts.exists(ref):
            continue
        proposal = ctx.artifacts.read(ref, ParagraphProposal)
        if any(item.id == paragraph_id_value for item in proposal.paragraphs):
            return proposal
    return None
