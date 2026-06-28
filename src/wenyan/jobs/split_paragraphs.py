from wenyan.core.adapters.hashing import sha256_text
from wenyan.core.adapters.prompt_template import RenderedPrompt, load_prompt_template
from wenyan.core.ports.artifact_ref import (
    chapter_proposal_ref,
    paragraph_proposal_ref,
    paragraph_proposal_validation_ref,
)
from wenyan.core.ports.artifact_store import ArtifactWrite
from wenyan.core.ports.prompt_context import PromptTextSlice
from wenyan.jobs.context import JobContext, JobOptions
from wenyan_models.artifacts.structure import ChapterProposal, ParagraphProposal, SpanValidationArtifact
from wenyan_models.domain.ids import ChapterId, DocumentId, paragraph_id
from wenyan_models.domain.results import JobFailure, JobOutcome, Promoted, Skipped
from wenyan_models.domain.spans import ParagraphSpan


def run_split_paragraphs(
    ctx: JobContext,
    document_id: DocumentId,
    chapter_id: ChapterId,
    options: JobOptions,
) -> JobOutcome[ParagraphProposal]:
    chapter_proposal = ctx.artifacts.read(
        chapter_proposal_ref(document_id),
        ChapterProposal,
    )
    chapter = next((item for item in chapter_proposal.chapters if item.id == chapter_id), None)
    if chapter is None:
        return JobFailure(code="missing-chapter", message="chapter not found in proposal")
    chapter_length = chapter.end - chapter.start
    proposal_ref = paragraph_proposal_ref(document_id, chapter_id)
    chapter_text = ctx.normalized_text.read_slice(document_id, chapter.start, chapter.end)
    input_hash = sha256_text(chapter_text)
    if ctx.artifacts.exists(proposal_ref) and not options.force:
        existing = ctx.artifacts.read(proposal_ref, ParagraphProposal)
        if existing.input_hash == input_hash:
            return Skipped(reason="paragraph proposal is current")
    template = load_prompt_template(
        ctx.repo_root / ctx.config.prompts.root,
        "paragraph-structure",
    )
    context = {
        "chapter_text": PromptTextSlice(document_id, chapter.start, chapter.end),
        "document_id": str(document_id),
        "chapter_id": str(chapter_id),
        "input_hash": str(input_hash),
        "chapter_text_hash": str(input_hash),
    }
    proposal = ctx.llm.complete_model(
        RenderedPrompt(template, context, normalized_text=ctx.normalized_text),
        ParagraphProposal,
    )
    proposal = proposal.model_copy(
        update={
            "document_id": document_id,
            "chapter_id": chapter_id,
            "input_hash": input_hash,
            "chapter_text_hash": input_hash,
            "model": ctx.config.models.active_model,
            "attempts": 1,
        },
    )
    paragraph_spans = tuple(
        ParagraphSpan(id=paragraph_id(str(item.id)), start=item.start, end=item.end)
        for item in proposal.paragraphs
    )
    validation = ctx.spans.validate_paragraphs(chapter_length, paragraph_spans)
    if validation.status.value == "failed":
        return JobFailure(code="validation", message="paragraph span validation failed")
    validation_artifact = SpanValidationArtifact(
        status=validation.status,
        checks=validation.checks,
    )
    if options.dry_run:
        return Promoted(artifact=proposal)
    ctx.artifacts.write_batch(
        [
            ArtifactWrite(ref=proposal_ref, payload=proposal),
            ArtifactWrite(
                ref=paragraph_proposal_validation_ref(document_id, chapter_id),
                payload=validation_artifact,
            ),
        ],
        dry_run=False,
    )
    return Promoted(artifact=proposal)
