from wenyan.core.adapters.hashing import sha256_text
from wenyan.core.adapters.prompt_template import RenderedPrompt, load_prompt_template
from wenyan.core.ports.artifact_ref import (
    chapter_proposal_ref,
    chapter_proposal_validation_ref,
    normalized_document_ref,
)
from wenyan.core.ports.artifact_store import ArtifactWrite
from wenyan.jobs.context import JobContext, JobOptions
from wenyan_models.artifacts.normalized import NormalizedDocument
from wenyan_models.artifacts.structure import ChapterProposal, SpanValidationArtifact
from wenyan_models.domain.ids import DocumentId, chapter_id, prompt_version
from wenyan_models.domain.results import JobFailure, JobOutcome, Promoted, Skipped
from wenyan_models.domain.spans import ChapterSpan


def run_split_chapters(
    ctx: JobContext,
    document_id: DocumentId,
    options: JobOptions,
) -> JobOutcome[ChapterProposal]:
    normalized_ref = normalized_document_ref(document_id)
    if not ctx.artifacts.exists(normalized_ref):
        return JobFailure(code="missing-input", message="normalized document is missing")
    normalized = ctx.artifacts.read(normalized_ref, NormalizedDocument)
    proposal_ref = chapter_proposal_ref(document_id)
    prompt_version_value = prompt_version("chapter-structure-v1")
    input_hash = sha256_text(normalized.normalized_hash)
    if ctx.artifacts.exists(proposal_ref) and not options.force:
        existing = ctx.artifacts.read(proposal_ref, ChapterProposal)
        if (
            existing.input_hash == input_hash
            and existing.prompt_version == prompt_version_value
        ):
            return Skipped(reason="chapter proposal is current")
    context = {
        "document_text": normalized.text,
        "document_id": str(document_id),
        "input_hash": str(input_hash),
        "source_hash": str(normalized.source_hash),
    }
    template = load_prompt_template(
        ctx.repo_root / ctx.config.prompts.root,
        "chapter-structure",
        "v1",
    )
    proposal = ctx.llm.complete_model(RenderedPrompt(template, context), ChapterProposal)
    proposal = proposal.model_copy(
        update={
            "document_id": document_id,
            "input_hash": input_hash,
            "source_hash": normalized.source_hash,
            "prompt_version": prompt_version_value,
            "model": ctx.config.models.active_model,
            "attempts": 1,
        },
    )
    chapter_spans = tuple(
        ChapterSpan(
            id=chapter_id(str(item.id)),
            title=item.title,
            start=item.start,
            end=item.end,
        )
        for item in proposal.chapters
    )
    validation = ctx.spans.validate_chapters(normalized.text, chapter_spans)
    if validation.status.value == "failed":
        return JobFailure(code="validation", message="chapter span validation failed")
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
                ref=chapter_proposal_validation_ref(document_id),
                payload=validation_artifact,
            ),
        ],
        dry_run=False,
    )
    return Promoted(artifact=proposal)
