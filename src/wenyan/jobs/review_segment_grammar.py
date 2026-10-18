from wenyan.core.hashing import sha256_text
from wenyan.core.ports.artifact_ref import (
    segment_grammar_notes_ref,
    segment_grammar_review_ref,
    segment_glosses_ref,
    segment_input_ref,
    segment_tokenization_ref,
)
from wenyan.jobs.context import JobContext, JobOptions
from wenyan.jobs.segment_runner import SegmentReviewJobSpec, run_segment_review_job
from wenyan_models.artifacts.segment import (
    GlossesArtifact,
    GrammarNotesArtifact,
    GrammarReviewArtifact,
    SegmentInput,
    TokenizationArtifact,
)
from wenyan_models.domain.ids import ContentHash, DocumentId, SegmentId
from wenyan_models.domain.results import JobFailure, JobOutcome


def _prepare_grammar_review(
    ctx: JobContext,
    document_id: DocumentId,
    segment_id_value: SegmentId,
    options: JobOptions,
) -> JobFailure | tuple[ContentHash, dict[str, str]]:
    del options
    grammar_ref = segment_grammar_notes_ref(document_id, segment_id_value)
    if not ctx.artifacts.exists(grammar_ref):
        return JobFailure(code="missing-input", message="grammar notes artifact is missing")
    grammar_notes = ctx.artifacts.read(grammar_ref, GrammarNotesArtifact)
    input_ref = segment_input_ref(document_id, segment_id_value)
    tokenization_ref = segment_tokenization_ref(document_id, segment_id_value)
    if not ctx.artifacts.exists(input_ref) or not ctx.artifacts.exists(tokenization_ref):
        return JobFailure(
            code="missing-input",
            message="segment input and tokenization are required for grammar review",
        )
    segment_input = ctx.artifacts.read(input_ref, SegmentInput)
    tokenization = ctx.artifacts.read(tokenization_ref, TokenizationArtifact)
    input_hash = sha256_text(grammar_notes.model_dump_json(by_alias=True))
    glosses_json = "null"
    glosses_ref = segment_glosses_ref(document_id, segment_id_value)
    if ctx.artifacts.exists(glosses_ref):
        glosses = ctx.artifacts.read(glosses_ref, GlossesArtifact)
        glosses_json = glosses.model_dump_json(by_alias=True)
    context = {
        "segment_id": str(segment_id_value),
        "review_input_hash": str(input_hash),
        "segment_text": segment_input.segment_text,
        "tokenization_json": tokenization.model_dump_json(by_alias=True),
        "grammar_notes_json": grammar_notes.model_dump_json(by_alias=True),
        "glosses_json": glosses_json,
        "local_context_json": segment_input.local_context.model_dump_json(by_alias=True),
    }
    return input_hash, context


_GRAMMAR_REVIEW_SPEC = SegmentReviewJobSpec(
    prompt_name="segment-grammar-review",
    output_model=GrammarReviewArtifact,
    review_ref=segment_grammar_review_ref,
    skip_reason="grammar review is current",
    reject_message="grammar review rejected",
    prepare=_prepare_grammar_review,
)


def run_review_segment_grammar(
    ctx: JobContext,
    document_id: DocumentId,
    segment_id_value: SegmentId,
    options: JobOptions,
) -> JobOutcome[GrammarReviewArtifact]:
    return run_segment_review_job(
        ctx,
        document_id,
        segment_id_value,
        options,
        _GRAMMAR_REVIEW_SPEC,
    )
