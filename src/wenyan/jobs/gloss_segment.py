import json

from wenyan.core.adapters.hashing import sha256_text
from wenyan.core.gloss.glossary_draft import (
    load_candidate_glosses,
    normalize_gloss_reuse,
)
from wenyan.core.ports.artifact_ref import (
    segment_glosses_ref,
    segment_input_ref,
    segment_tokenization_ref,
)
from wenyan.jobs.context import JobContext, JobOptions
from wenyan.jobs.segment_runner import (
    SegmentAnnotateJobSpec,
    load_approved_tokenization_review,
    run_segment_annotate_job,
    run_segment_batch,
)
from wenyan_models.artifacts.segment import GlossesArtifact, TokenizationArtifact
from wenyan_models.domain.enums import ComponentKind
from wenyan_models.domain.ids import ContentHash, DocumentId, SegmentId
from wenyan_models.domain.results import JobFailure, JobOutcome
from wenyan_models.domain.targets import SegmentTarget


def _prepare_gloss(
    ctx: JobContext,
    document_id: DocumentId,
    segment_id_value: SegmentId,
    options: JobOptions,
) -> JobFailure | tuple[ContentHash, dict[str, str]]:
    del options
    upstream = load_approved_tokenization_review(
        ctx,
        document_id,
        segment_id_value,
        missing_review_message="approved tokenization review is required before glossing",
        blocked_message="tokenization review must be approved before glossing",
    )
    if isinstance(upstream, JobFailure):
        return upstream
    tokenization, tokenization_review = upstream
    input_ref = segment_input_ref(document_id, segment_id_value)
    if not ctx.artifacts.exists(input_ref):
        return JobFailure(code="missing-input", message="segment input is missing")
    input_hash = sha256_text(tokenization_review.model_dump_json(by_alias=True))
    all_candidates = load_candidate_glosses(ctx.artifacts, document_id, segment_id_value)
    context = {
        "segment_id": str(segment_id_value),
        "segment_text": tokenization.text,
        "input_hash": str(input_hash),
        "tokenization_json": tokenization.model_dump_json(by_alias=True),
        "candidate_glosses_json": json.dumps(
            [entry.model_dump(by_alias=True) for entry in all_candidates],
            ensure_ascii=False,
        ),
    }
    return input_hash, context


def _post_process_gloss(
    glosses: GlossesArtifact,
    ctx: JobContext,
    document_id: DocumentId,
    segment_id_value: SegmentId,
    input_hash: ContentHash,
) -> GlossesArtifact:
    del input_hash
    tokenization = ctx.artifacts.read(
        segment_tokenization_ref(document_id, segment_id_value),
        TokenizationArtifact,
    )
    all_candidates = load_candidate_glosses(ctx.artifacts, document_id, segment_id_value)
    return normalize_gloss_reuse(glosses, tokenization, all_candidates)


_GLOSS_SPEC = SegmentAnnotateJobSpec(
    prompt_name="segment-gloss",
    output_model=GlossesArtifact,
    artifact_ref=segment_glosses_ref,
    component_kind=ComponentKind.GLOSS_SEGMENT,
    skip_reason="glosses are current",
    prepare=_prepare_gloss,
    post_process=_post_process_gloss,
)


def run_gloss_segment(
    ctx: JobContext,
    document_id: DocumentId,
    target: SegmentTarget,
    options: JobOptions,
) -> JobOutcome[GlossesArtifact]:
    return run_segment_batch(
        ctx,
        document_id,
        target,
        options,
        empty_message="no segments to gloss",
        all_skipped_reason="all segments already glossed",
        run_one=_gloss_one,
    )


def _gloss_one(
    ctx: JobContext,
    document_id: DocumentId,
    segment_id_value: SegmentId,
    options: JobOptions,
) -> JobOutcome[GlossesArtifact]:
    return run_segment_annotate_job(ctx, document_id, segment_id_value, options, _GLOSS_SPEC)
