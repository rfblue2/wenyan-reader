import json

from wenyan.core.gloss.filter_candidates import filter_candidates_by_token_surfaces
from wenyan.core.gloss.glossary_draft import (
    load_candidate_glosses,
    normalize_gloss_reuse,
)
from wenyan.core.hashing import sha256_text
from wenyan.core.ports.artifact_ref import SegmentArtifactKind, SegmentRef
from wenyan.core.run.segment_pipeline import GLOSS_STAGE
from wenyan.jobs.context import JobContext, JobOptions
from wenyan.jobs.segment_runner import (
    Prepared,
    SegmentAnnotateJobSpec,
    load_approved_tokenization_review,
    run_segment_job,
)
from wenyan_models.artifacts.segment import GlossesArtifact, TokenizationArtifact
from wenyan_models.domain.ids import DocumentId, SegmentId
from wenyan_models.domain.results import JobFailure, JobOutcome
from wenyan_models.domain.targets import SegmentTarget


def _prepare_gloss(
    ctx: JobContext,
    document_id: DocumentId,
    segment_id_value: SegmentId,
) -> JobFailure | Prepared:
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
    input_ref = SegmentRef(SegmentArtifactKind.INPUT, document_id, segment_id_value)
    if not ctx.artifacts.exists(input_ref):
        return JobFailure(code="missing-input", message="segment input is missing")
    input_hash = sha256_text(tokenization_review.model_dump_json(by_alias=True))
    all_candidates = load_candidate_glosses(ctx.artifacts, document_id, segment_id_value)
    prompt_candidates = filter_candidates_by_token_surfaces(all_candidates, tokenization)
    context = {
        "segment_id": str(segment_id_value),
        "segment_text": tokenization.text,
        "input_hash": str(input_hash),
        "tokenization_json": tokenization.model_dump_json(by_alias=True),
        "candidate_glosses_json": json.dumps(
            [entry.model_dump(by_alias=True) for entry in prompt_candidates],
            ensure_ascii=False,
        ),
    }
    return Prepared(input_hash, context)


def _post_process_gloss(
    glosses: GlossesArtifact,
    ctx: JobContext,
    document_id: DocumentId,
    segment_id_value: SegmentId,
) -> GlossesArtifact:
    tokenization = ctx.artifacts.read(
        SegmentRef(SegmentArtifactKind.TOKENIZATION, document_id, segment_id_value),
        TokenizationArtifact,
    )
    all_candidates = load_candidate_glosses(ctx.artifacts, document_id, segment_id_value)
    return normalize_gloss_reuse(glosses, tokenization, all_candidates)


_GLOSS_SPEC = SegmentAnnotateJobSpec(
    stage=GLOSS_STAGE,
    prompt_name="segment-gloss",
    output_model=GlossesArtifact,
    prepare=_prepare_gloss,
    post_process=_post_process_gloss,
    empty_message="no segments to gloss",
    skip_reason="all segments already glossed",
)


def run_gloss_segment(
    ctx: JobContext,
    document_id: DocumentId,
    target: SegmentTarget,
    options: JobOptions,
) -> JobOutcome[GlossesArtifact]:
    return run_segment_job(ctx, document_id, target, options, _GLOSS_SPEC)
