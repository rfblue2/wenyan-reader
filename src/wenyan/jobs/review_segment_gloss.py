from wenyan.core.gloss.glossary_draft import (
    load_candidate_glosses,
    load_glossary_draft,
    merge_approved_glosses,
    save_glossary_draft,
)
import json

from wenyan.core.adapters.hashing import sha256_text
from wenyan.core.adapters.prompt_template import RenderedPrompt, load_prompt_template
from wenyan.core.ports.artifact_ref import (
    segment_gloss_review_ref,
    segment_glosses_ref,
    segment_input_ref,
    segment_tokenization_ref,
)
from wenyan.jobs.context import JobContext, JobOptions
from wenyan_models.artifacts.segment import GlossReviewArtifact, GlossesArtifact, SegmentInput, TokenizationArtifact
from wenyan_models.domain.enums import ReviewStatus
from wenyan_models.domain.ids import DocumentId, SegmentId
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
    input_ref = segment_input_ref(document_id, segment_id_value)
    tokenization_ref = segment_tokenization_ref(document_id, segment_id_value)
    if not ctx.artifacts.exists(input_ref) or not ctx.artifacts.exists(tokenization_ref):
        return JobFailure(code="missing-input", message="segment input and tokenization are required for gloss review")
    segment_input = ctx.artifacts.read(input_ref, SegmentInput)
    tokenization = ctx.artifacts.read(tokenization_ref, TokenizationArtifact)
    review_ref = segment_gloss_review_ref(document_id, segment_id_value)
    input_hash = sha256_text(glosses.model_dump_json(by_alias=True))
    if ctx.artifacts.exists(review_ref) and not options.force:
        existing = ctx.artifacts.read(review_ref, GlossReviewArtifact)
        if existing.input_hash == input_hash:
            return Skipped(reason="gloss review is current")
    template = load_prompt_template(
        ctx.repo_root / ctx.config.prompts.root,
        "segment-gloss-review",
    )
    context = {
        "segment_id": str(segment_id_value),
        "review_input_hash": str(input_hash),
        "segment_text": segment_input.segment_text,
        "tokenization_json": tokenization.model_dump_json(by_alias=True),
        "glosses_json": glosses.model_dump_json(by_alias=True),
        "candidate_glosses_json": json.dumps(
            [
                entry.model_dump(by_alias=True)
                for entry in load_candidate_glosses(ctx.artifacts, document_id, segment_id_value)
            ],
            ensure_ascii=False,
        ),
    }
    review = ctx.llm.complete_model(RenderedPrompt(template, context), GlossReviewArtifact)
    review = review.model_copy(
        update={
            "segment_id": segment_id_value,
            "input_hash": input_hash,
            "model": ctx.config.models.active_model,
            "attempts": 1,
        },
    )
    if options.dry_run:
        return Promoted(artifact=review)
    ctx.artifacts.write(review_ref, review, dry_run=False)
    if review.status == ReviewStatus.REJECTED:
        return JobFailure(code="review-rejected", message="gloss review rejected")
    if not options.dry_run:
        draft = merge_approved_glosses(load_glossary_draft(ctx.artifacts, document_id), glosses)
        save_glossary_draft(ctx.artifacts, document_id, draft, dry_run=False)
    return Promoted(artifact=review)
