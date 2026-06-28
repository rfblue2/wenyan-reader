from wenyan.core.adapters.hashing import sha256_text
from wenyan.core.adapters.prompt_template import RenderedPrompt, load_prompt_template
from wenyan.core.ports.artifact_ref import segment_gloss_review_ref, segment_glosses_ref
from wenyan.jobs.context import JobContext, JobOptions
from wenyan_models.artifacts.segment import GlossReviewArtifact, GlossesArtifact
from wenyan_models.domain.enums import ReviewStatus
from wenyan_models.domain.ids import DocumentId, SegmentId, prompt_version
from wenyan_models.domain.results import JobFailure, JobOutcome, Promoted, Skipped


def run_review_segment_gloss(
    ctx: JobContext,
    document_id: DocumentId,
    segment_id_value: SegmentId,
    options: JobOptions,
) -> JobOutcome[GlossReviewArtifact]:
    glosses_ref = segment_glosses_ref(document_id, segment_id_value)
    if not ctx.artifacts.exists(glosses_ref):
        return JobFailure(code="missing-input", message="glosses artifact is missing")
    glosses = ctx.artifacts.read(glosses_ref, GlossesArtifact)
    review_ref = segment_gloss_review_ref(document_id, segment_id_value)
    prompt_version_value = prompt_version("segment-gloss-review-v1")
    input_hash = sha256_text(glosses.model_dump_json(by_alias=True))
    if ctx.artifacts.exists(review_ref) and not options.force:
        existing = ctx.artifacts.read(review_ref, GlossReviewArtifact)
        if (
            existing.input_hash == input_hash
            and existing.prompt_version == prompt_version_value
        ):
            return Skipped(reason="gloss review is current")
    template = load_prompt_template(
        ctx.repo_root / ctx.config.prompts.root,
        "segment-gloss-review",
        "v1",
    )
    context = {
        "segment_id": str(segment_id_value),
        "review_input_hash": str(input_hash),
        "glosses_json": glosses.model_dump_json(by_alias=True),
    }
    review = ctx.llm.complete_model(RenderedPrompt(template, context), GlossReviewArtifact)
    review = review.model_copy(
        update={
            "segment_id": segment_id_value,
            "input_hash": input_hash,
            "prompt_version": prompt_version_value,
            "model": ctx.config.models.active_model,
            "attempts": 1,
        },
    )
    if options.dry_run:
        return Promoted(artifact=review)
    ctx.artifacts.write(review_ref, review, dry_run=False)
    if review.status == ReviewStatus.REJECTED:
        return JobFailure(code="review-rejected", message="gloss review rejected")
    return Promoted(artifact=review)
