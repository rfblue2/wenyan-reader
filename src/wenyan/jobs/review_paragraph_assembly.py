from wenyan.core.adapters.hashing import sha256_text
from wenyan.core.adapters.prompt_template import RenderedPrompt, load_prompt_template
from wenyan.core.ports.artifact_ref import (
    paragraph_assembly_package_ref,
    paragraph_assembly_review_ref,
    paragraph_draft_ref,
)
from wenyan.jobs.context import JobContext, JobOptions
from wenyan_models.artifacts.assembly import ParagraphAssemblyReviewArtifact
from wenyan_models.artifacts.paragraph import ParagraphDraft
from wenyan_models.domain.enums import ReviewStatus
from wenyan_models.domain.ids import DocumentId, ParagraphId
from wenyan_models.domain.results import JobFailure, JobOutcome, Promoted, Skipped
from wenyan_models.reader.paragraph import ParagraphPackage


def run_review_paragraph_assembly(
    ctx: JobContext,
    document_id: DocumentId,
    paragraph_id_value: ParagraphId,
    options: JobOptions,
) -> JobOutcome[ParagraphAssemblyReviewArtifact]:
    package_ref = paragraph_assembly_package_ref(document_id, paragraph_id_value)
    if not ctx.artifacts.exists(package_ref):
        return JobFailure(code="missing-input", message="paragraph assembly package is missing")
    package = ctx.artifacts.read(package_ref, ParagraphPackage)
    input_hash = sha256_text(package.model_dump_json(by_alias=True))
    review_ref = paragraph_assembly_review_ref(document_id, paragraph_id_value)
    if ctx.artifacts.exists(review_ref) and not options.force:
        existing = ctx.artifacts.read(review_ref, ParagraphAssemblyReviewArtifact)
        if existing.input_hash == input_hash:
            return Skipped(reason="paragraph assembly review is current")
    template = load_prompt_template(
        ctx.repo_root / ctx.config.prompts.root,
        "review-paragraph-assembly",
    )
    draft = ctx.artifacts.read(
        paragraph_draft_ref(document_id, paragraph_id_value),
        ParagraphDraft,
    )
    context = {
        "paragraph_id": str(paragraph_id_value),
        "review_input_hash": str(input_hash),
        "paragraph_package_json": package.model_dump_json(by_alias=True),
        "paragraph_draft_json": draft.model_dump_json(by_alias=True),
    }
    review = ctx.llm.complete_model(RenderedPrompt(template, context), ParagraphAssemblyReviewArtifact)
    review = review.model_copy(
        update={
            "paragraph_id": paragraph_id_value,
            "input_hash": input_hash,
            "model": ctx.config.models.active_model,
            "attempts": 1,
        },
    )
    if options.dry_run:
        return Promoted(artifact=review)
    ctx.artifacts.write(review_ref, review, dry_run=False)
    if review.status == ReviewStatus.REJECTED:
        return JobFailure(code="review-rejected", message="paragraph assembly review rejected")
    return Promoted(artifact=review)
