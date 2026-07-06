from wenyan.core.adapters.hashing import sha256_text
from wenyan.core.ports.artifact_ref import segment_input_ref, segment_tokenization_ref
from wenyan.jobs.context import JobContext, JobOptions
from wenyan.jobs.segment_runner import (
    SegmentAnnotateJobSpec,
    run_segment_annotate_job,
    run_segment_batch,
)
from wenyan_models.artifacts.segment import SegmentInput, TokenizationArtifact
from wenyan_models.text.tokenization import drop_punctuation_tokens
from wenyan_models.domain.enums import ComponentKind
from wenyan_models.domain.ids import ContentHash, DocumentId, SegmentId
from wenyan_models.domain.results import JobFailure, JobOutcome
from wenyan_models.domain.targets import SegmentTarget


def _prepare_tokenize(
    ctx: JobContext,
    document_id: DocumentId,
    segment_id_value: SegmentId,
    options: JobOptions,
) -> JobFailure | tuple[ContentHash, dict[str, str]]:
    del options
    input_ref = segment_input_ref(document_id, segment_id_value)
    if not ctx.artifacts.exists(input_ref):
        return JobFailure(code="missing-input", message="segment input is missing")
    segment_input = ctx.artifacts.read(input_ref, SegmentInput)
    input_hash = sha256_text(segment_input.segment_text)
    context = {
        "segment_text": segment_input.segment_text,
        "segment_id": str(segment_id_value),
        "input_hash": str(input_hash),
    }
    return input_hash, context


def _post_process_tokenize(
    artifact: TokenizationArtifact,
    ctx: JobContext,
    document_id: DocumentId,
    segment_id_value: SegmentId,
    input_hash: ContentHash,
) -> TokenizationArtifact:
    del ctx, document_id, segment_id_value, input_hash
    return artifact.model_copy(update={"tokens": drop_punctuation_tokens(artifact.tokens)})


_TOKENIZE_SPEC = SegmentAnnotateJobSpec(
    prompt_name="segment-tokenization",
    output_model=TokenizationArtifact,
    artifact_ref=segment_tokenization_ref,
    component_kind=ComponentKind.TOKENIZE_SEGMENT,
    skip_reason="tokenization is current",
    prepare=_prepare_tokenize,
    post_process=_post_process_tokenize,
)


def run_tokenize_segment(
    ctx: JobContext,
    document_id: DocumentId,
    target: SegmentTarget,
    options: JobOptions,
) -> JobOutcome[TokenizationArtifact]:
    return run_segment_batch(
        ctx,
        document_id,
        target,
        options,
        empty_message="no segments to tokenize",
        all_skipped_reason="all segments already tokenized",
        run_one=_tokenize_one,
    )


def _tokenize_one(
    ctx: JobContext,
    document_id: DocumentId,
    segment_id_value: SegmentId,
    options: JobOptions,
) -> JobOutcome[TokenizationArtifact]:
    return run_segment_annotate_job(ctx, document_id, segment_id_value, options, _TOKENIZE_SPEC)
