from wenyan.core.adapters.hashing import sha256_text
from wenyan.core.adapters.prompt_template import RenderedPrompt, load_prompt_template
from wenyan.core.ports.artifact_ref import (
    chapter_proposal_ref,
    normalized_document_ref,
    paragraph_draft_ref,
    paragraph_draft_validation_ref,
    paragraph_proposal_ref,
    segment_input_ref,
)
from wenyan.core.ports.artifact_store import ArtifactWrite
from wenyan.jobs.context import JobContext, JobOptions
from wenyan_models.artifacts.normalized import NormalizedDocument
from wenyan_models.artifacts.paragraph import ParagraphDraft, ParagraphValidationArtifact
from wenyan_models.artifacts.segment import SegmentInput
from wenyan_models.domain.enums import ValidationStatus
from wenyan_models.artifacts.structure import ChapterProposal, ParagraphProposal
from wenyan_models.domain.ids import DocumentId, ParagraphId, chapter_id, prompt_version, segment_id
from wenyan_models.domain.results import JobFailure, JobOutcome, Promoted, Skipped


def run_split_segments(
    ctx: JobContext,
    document_id: DocumentId,
    paragraph_id_value: ParagraphId,
    options: JobOptions,
) -> JobOutcome[ParagraphDraft]:
    normalized = ctx.artifacts.read(
        normalized_document_ref(document_id),
        NormalizedDocument,
    )
    chapter_proposal = ctx.artifacts.read(chapter_proposal_ref(document_id), ChapterProposal)
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
    paragraph_text = normalized.text[chapter.start + paragraph_item.start : chapter.start + paragraph_item.end]
    draft_ref = paragraph_draft_ref(document_id, paragraph_id_value)
    prompt_version_value = prompt_version("paragraph-segmentation-v1")
    input_hash = sha256_text(paragraph_text)
    if ctx.artifacts.exists(draft_ref) and not options.force:
        existing = ctx.artifacts.read(draft_ref, ParagraphDraft)
        if (
            existing.input_hash == input_hash
            and existing.prompt_version == prompt_version_value
        ):
            return Skipped(reason="paragraph draft is current")
    template = load_prompt_template(
        ctx.repo_root / ctx.config.prompts.root,
        "paragraph-segmentation",
        "v1",
    )
    context = {
        "paragraph_text": paragraph_text,
        "paragraph_id": str(paragraph_id_value),
        "input_hash": str(input_hash),
    }
    draft = ctx.llm.complete_model(RenderedPrompt(template, context), ParagraphDraft)
    draft = draft.model_copy(
        update={
            "paragraph_id": paragraph_id_value,
            "input_hash": input_hash,
            "prompt_version": prompt_version_value,
            "model": ctx.config.models.active_model,
            "attempts": 1,
        },
    )
    validation = ParagraphValidationArtifact(status=ValidationStatus.PASSED, checks=())
    writes: list[ArtifactWrite] = [
        ArtifactWrite(ref=draft_ref, payload=draft),
        ArtifactWrite(
            ref=paragraph_draft_validation_ref(document_id, paragraph_id_value),
            payload=validation,
        ),
    ]
    for segment in draft.segments:
        writes.append(
            ArtifactWrite(
                ref=segment_input_ref(document_id, segment_id(str(segment.id))),
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
        ref = paragraph_proposal_ref(document_id, chapter_id(str(chapter.id)))
        if not ctx.artifacts.exists(ref):
            continue
        proposal = ctx.artifacts.read(ref, ParagraphProposal)
        if any(item.id == paragraph_id_value for item in proposal.paragraphs):
            return proposal
    return None
