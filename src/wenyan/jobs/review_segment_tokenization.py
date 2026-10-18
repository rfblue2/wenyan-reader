from wenyan.core.hashing import sha256_text
from wenyan.core.ports.artifact_ref import segment_tokenization_ref, segment_tokenization_review_ref
from wenyan.jobs.context import JobContext, JobOptions
from wenyan.jobs.segment_runner import SegmentReviewJobSpec, run_segment_review_job
from wenyan_models.artifacts.segment import TokenizationArtifact, TokenizationReviewArtifact
from wenyan_models.domain.ids import ContentHash, DocumentId, SegmentId
from wenyan_models.domain.results import JobFailure, JobOutcome


def _prepare_tokenization_review(
    ctx: JobContext,
    document_id: DocumentId,
    segment_id_value: SegmentId,
    options: JobOptions,
) -> JobFailure | tuple[ContentHash, dict[str, str]]:
    del options
    tokenization_ref = segment_tokenization_ref(document_id, segment_id_value)
    if not ctx.artifacts.exists(tokenization_ref):
        return JobFailure(code="missing-input", message="tokenization artifact is missing")
    tokenization = ctx.artifacts.read(tokenization_ref, TokenizationArtifact)
    input_hash = sha256_text(tokenization.model_dump_json(by_alias=True))
    context = {
        "segment_id": str(segment_id_value),
        "review_input_hash": str(input_hash),
        "tokenization_json": tokenization.model_dump_json(by_alias=True),
    }
    return input_hash, context


_TOKENIZATION_REVIEW_SPEC = SegmentReviewJobSpec(
    prompt_name="segment-tokenization-review",
    output_model=TokenizationReviewArtifact,
    review_ref=segment_tokenization_review_ref,
    skip_reason="tokenization review is current",
    reject_message="tokenization review rejected",
    prepare=_prepare_tokenization_review,
)


def run_review_segment_tokenization(
    ctx: JobContext,
    document_id: DocumentId,
    segment_id_value: SegmentId,
    options: JobOptions,
) -> JobOutcome[TokenizationReviewArtifact]:
    return run_segment_review_job(
        ctx,
        document_id,
        segment_id_value,
        options,
        _TOKENIZATION_REVIEW_SPEC,
    )
