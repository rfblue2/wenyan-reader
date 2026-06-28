from wenyan.core.adapters.hashing import sha256_text
from wenyan.core.adapters.prompt_template import RenderedPrompt, load_prompt_template
from wenyan.core.ports.artifact_ref import (
    chapter_proposal_ref,
    normalized_document_ref,
    paragraph_proposal_ref,
    paragraph_proposal_validation_ref,
)
from wenyan.core.ports.artifact_store import ArtifactWrite
from wenyan.jobs.context import JobContext, JobOptions
from wenyan_models.artifacts.normalized import NormalizedDocument
from wenyan_models.artifacts.structure import ChapterProposal, ParagraphProposal, SpanValidationArtifact
from wenyan_models.domain.ids import ChapterId, DocumentId, paragraph_id, prompt_version
from wenyan_models.domain.results import JobFailure, JobOutcome, Promoted, Skipped
from wenyan_models.domain.spans import ParagraphSpan


def run_split_paragraphs(
    ctx: JobContext,
    document_id: DocumentId,
    chapter_id: ChapterId,
    options: JobOptions,
) -> JobOutcome[ParagraphProposal]:
    normalized = ctx.artifacts.read(
        normalized_document_ref(document_id),
        NormalizedDocument,
    )
    chapter_proposal = ctx.artifacts.read(
        chapter_proposal_ref(document_id),
        ChapterProposal,
    )
    chapter = next((item for item in chapter_proposal.chapters if item.id == chapter_id), None)
    if chapter is None:
        return JobFailure(code="missing-chapter", message="chapter not found in proposal")
    chapter_text = normalized.text[chapter.start : chapter.end]
    proposal_ref = paragraph_proposal_ref(document_id, chapter_id)
    prompt_version_value = prompt_version("paragraph-structure-v1")
    input_hash = sha256_text(chapter_text)
    if ctx.artifacts.exists(proposal_ref) and not options.force:
        existing = ctx.artifacts.read(proposal_ref, ParagraphProposal)
        if (
            existing.input_hash == input_hash
            and existing.prompt_version == prompt_version_value
        ):
            return Skipped(reason="paragraph proposal is current")
    template = load_prompt_template(
        ctx.repo_root / ctx.config.prompts.root,
        "paragraph-structure",
        "v1",
    )
    context = {
        "chapter_text": chapter_text,
        "document_id": str(document_id),
        "chapter_id": str(chapter_id),
        "input_hash": str(input_hash),
        "chapter_text_hash": str(input_hash),
    }
    proposal = ctx.llm.complete_model(RenderedPrompt(template, context), ParagraphProposal)
    proposal = proposal.model_copy(
        update={
            "document_id": document_id,
            "chapter_id": chapter_id,
            "input_hash": input_hash,
            "chapter_text_hash": input_hash,
            "prompt_version": prompt_version_value,
            "model": ctx.config.models.active_model,
            "attempts": 1,
        },
    )
    paragraph_spans = tuple(
        ParagraphSpan(id=paragraph_id(str(item.id)), start=item.start, end=item.end)
        for item in proposal.paragraphs
    )
    validation = ctx.spans.validate_paragraphs(chapter_text, paragraph_spans)
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
