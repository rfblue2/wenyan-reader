import json

from wenyan.core.adapters.hashing import sha256_text
from wenyan.core.gloss.glossary_draft import (
    load_candidate_glosses,
    load_glossary_draft,
    merge_approved_glosses,
    save_glossary_draft,
)
from wenyan.core.ports.artifact_ref import (
    segment_gloss_review_ref,
    segment_glosses_ref,
    segment_input_ref,
    segment_tokenization_ref,
)
from wenyan.jobs.context import JobContext, JobOptions
from wenyan.jobs.segment_runner import SegmentReviewJobSpec, run_segment_review_job
from wenyan_models.artifacts.segment import GlossReviewArtifact, GlossesArtifact, SegmentInput, TokenizationArtifact
from wenyan_models.domain.ids import ContentHash, DocumentId, SegmentId
from wenyan_models.domain.results import JobFailure, JobOutcome


def _prepare_gloss_review(
    ctx: JobContext,
    document_id: DocumentId,
    segment_id_value: SegmentId,
    options: JobOptions,
) -> JobFailure | tuple[ContentHash, dict[str, str]]:
    del options
    glosses_ref = segment_glosses_ref(document_id, segment_id_value)
    if not ctx.artifacts.exists(glosses_ref):
        return JobFailure(code="missing-input", message="glosses artifact is missing")
    glosses = ctx.artifacts.read(glosses_ref, GlossesArtifact)
    input_ref = segment_input_ref(document_id, segment_id_value)
    tokenization_ref = segment_tokenization_ref(document_id, segment_id_value)
    if not ctx.artifacts.exists(input_ref) or not ctx.artifacts.exists(tokenization_ref):
        return JobFailure(
            code="missing-input",
            message="segment input and tokenization are required for gloss review",
        )
    segment_input = ctx.artifacts.read(input_ref, SegmentInput)
    tokenization = ctx.artifacts.read(tokenization_ref, TokenizationArtifact)
    input_hash = sha256_text(glosses.model_dump_json(by_alias=True))
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
    return input_hash, context


def _merge_glossary_after_gloss_review(
    ctx: JobContext,
    document_id: DocumentId,
    segment_id_value: SegmentId,
    review: GlossReviewArtifact,
    options: JobOptions,
) -> None:
    del review, options
    glosses = ctx.artifacts.read(
        segment_glosses_ref(document_id, segment_id_value),
        GlossesArtifact,
    )
    draft = merge_approved_glosses(load_glossary_draft(ctx.artifacts, document_id), glosses)
    save_glossary_draft(ctx.artifacts, document_id, draft, dry_run=False)


_GLOSS_REVIEW_SPEC = SegmentReviewJobSpec(
    prompt_name="segment-gloss-review",
    output_model=GlossReviewArtifact,
    review_ref=segment_gloss_review_ref,
    skip_reason="gloss review is current",
    reject_message="gloss review rejected",
    prepare=_prepare_gloss_review,
    post_write=_merge_glossary_after_gloss_review,
)


def run_review_segment_gloss(
    ctx: JobContext,
    document_id: DocumentId,
    segment_id_value: SegmentId,
    options: JobOptions,
) -> JobOutcome[GlossReviewArtifact]:
    return run_segment_review_job(
        ctx,
        document_id,
        segment_id_value,
        options,
        _GLOSS_REVIEW_SPEC,
    )
