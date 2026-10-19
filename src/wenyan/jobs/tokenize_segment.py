from wenyan.core.hashing import sha256_text
from wenyan.core.ports.artifact_ref import SegmentArtifactKind, SegmentRef
from wenyan.core.run.segment_pipeline import TOKENIZATION_STAGE
from wenyan.jobs.context import JobContext, JobOptions
from wenyan.jobs.segment_runner import Prepared, SegmentAnnotateJobSpec, run_segment_job
from wenyan_models.artifacts.segment import SegmentInput, TokenizationArtifact
from wenyan_models.text.tokenization import drop_punctuation_tokens
from wenyan_models.domain.ids import DocumentId, SegmentId
from wenyan_models.domain.results import JobFailure, JobOutcome
from wenyan_models.domain.targets import SegmentTarget


def _prepare_tokenize(
    ctx: JobContext,
    document_id: DocumentId,
    segment_id_value: SegmentId,
) -> JobFailure | Prepared:
    input_ref = SegmentRef(SegmentArtifactKind.INPUT, document_id, segment_id_value)
    if not ctx.artifacts.exists(input_ref):
        return JobFailure(code="missing-input", message="segment input is missing")
    segment_input = ctx.artifacts.read(input_ref, SegmentInput)
    input_hash = sha256_text(segment_input.segment_text)
    context = {
        "segment_text": segment_input.segment_text,
        "segment_id": str(segment_id_value),
        "input_hash": str(input_hash),
    }
    return Prepared(input_hash, context)


def _post_process_tokenize(
    artifact: TokenizationArtifact,
    ctx: JobContext,
    document_id: DocumentId,
    segment_id_value: SegmentId,
) -> TokenizationArtifact:
    del ctx, document_id, segment_id_value
    return artifact.model_copy(update={"tokens": drop_punctuation_tokens(artifact.tokens)})


_TOKENIZE_SPEC = SegmentAnnotateJobSpec(
    stage=TOKENIZATION_STAGE,
    prompt_name="segment-tokenization",
    output_model=TokenizationArtifact,
    prepare=_prepare_tokenize,
    post_process=_post_process_tokenize,
    empty_message="no segments to tokenize",
    skip_reason="all segments already tokenized",
)


def run_tokenize_segment(
    ctx: JobContext,
    document_id: DocumentId,
    target: SegmentTarget,
    options: JobOptions,
) -> JobOutcome[TokenizationArtifact]:
    return run_segment_job(ctx, document_id, target, options, _TOKENIZE_SPEC)
