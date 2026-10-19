from wenyan.core.hashing import sha256_text
from wenyan.core.ports.artifact_ref import SegmentArtifactKind, SegmentRef
from wenyan.core.run.segment_pipeline import TOKENIZATION_STAGE
from wenyan.jobs.context import JobContext, JobOptions
from wenyan.jobs.segment_runner import Prepared, SegmentReviewJobSpec, run_segment_job
from wenyan_models.artifacts.segment import SegmentReview, TokenizationArtifact
from wenyan_models.domain.ids import DocumentId, SegmentId
from wenyan_models.domain.results import JobFailure, JobOutcome
from wenyan_models.domain.targets import SegmentTarget


def _prepare_tokenization_review(
    ctx: JobContext,
    document_id: DocumentId,
    segment_id_value: SegmentId,
) -> JobFailure | Prepared:
    tokenization_ref = SegmentRef(SegmentArtifactKind.TOKENIZATION, document_id, segment_id_value)
    if not ctx.artifacts.exists(tokenization_ref):
        return JobFailure(code="missing-input", message="tokenization artifact is missing")
    tokenization = ctx.artifacts.read(tokenization_ref, TokenizationArtifact)
    input_hash = sha256_text(tokenization.model_dump_json(by_alias=True))
    context = {
        "segment_id": str(segment_id_value),
        "review_input_hash": str(input_hash),
        "tokenization_json": tokenization.model_dump_json(by_alias=True),
    }
    return Prepared(input_hash, context)


_TOKENIZATION_REVIEW_SPEC = SegmentReviewJobSpec(
    stage=TOKENIZATION_STAGE,
    prompt_name="segment-tokenization-review",
    prepare=_prepare_tokenization_review,
    empty_message="no segments to review",
    skip_reason="tokenization review is current",
    reject_message="tokenization review rejected",
)


def run_review_segment_tokenization(
    ctx: JobContext,
    document_id: DocumentId,
    target: SegmentTarget,
    options: JobOptions,
) -> JobOutcome[SegmentReview]:
    return run_segment_job(ctx, document_id, target, options, _TOKENIZATION_REVIEW_SPEC)
