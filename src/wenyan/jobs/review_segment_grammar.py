from wenyan.core.hashing import sha256_text
from wenyan.core.ports.artifact_ref import SegmentArtifactKind, SegmentRef
from wenyan.core.run.segment_pipeline import GRAMMAR_STAGE
from wenyan.jobs.context import JobContext, JobOptions
from wenyan.jobs.segment_runner import Prepared, SegmentReviewJobSpec, run_segment_job
from wenyan_models.artifacts.segment import (
    GlossesArtifact,
    GrammarNotesArtifact,
    SegmentInput,
    SegmentReview,
    TokenizationArtifact,
)
from wenyan_models.domain.ids import DocumentId, SegmentId
from wenyan_models.domain.results import JobFailure, JobOutcome
from wenyan_models.domain.targets import SegmentTarget


def _prepare_grammar_review(
    ctx: JobContext,
    document_id: DocumentId,
    segment_id_value: SegmentId,
) -> JobFailure | Prepared:
    grammar_ref = SegmentRef(SegmentArtifactKind.GRAMMAR_NOTES, document_id, segment_id_value)
    if not ctx.artifacts.exists(grammar_ref):
        return JobFailure(code="missing-input", message="grammar notes artifact is missing")
    grammar_notes = ctx.artifacts.read(grammar_ref, GrammarNotesArtifact)
    input_ref = SegmentRef(SegmentArtifactKind.INPUT, document_id, segment_id_value)
    tokenization_ref = SegmentRef(SegmentArtifactKind.TOKENIZATION, document_id, segment_id_value)
    if not ctx.artifacts.exists(input_ref) or not ctx.artifacts.exists(tokenization_ref):
        return JobFailure(
            code="missing-input",
            message="segment input and tokenization are required for grammar review",
        )
    segment_input = ctx.artifacts.read(input_ref, SegmentInput)
    tokenization = ctx.artifacts.read(tokenization_ref, TokenizationArtifact)
    input_hash = sha256_text(grammar_notes.model_dump_json(by_alias=True))
    glosses_json = "null"
    glosses_ref = SegmentRef(SegmentArtifactKind.GLOSSES, document_id, segment_id_value)
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
    return Prepared(input_hash, context)


_GRAMMAR_REVIEW_SPEC = SegmentReviewJobSpec(
    stage=GRAMMAR_STAGE,
    prompt_name="segment-grammar-review",
    prepare=_prepare_grammar_review,
    empty_message="no segments to review",
    skip_reason="grammar review is current",
    reject_message="grammar review rejected",
)


def run_review_segment_grammar(
    ctx: JobContext,
    document_id: DocumentId,
    target: SegmentTarget,
    options: JobOptions,
) -> JobOutcome[SegmentReview]:
    return run_segment_job(ctx, document_id, target, options, _GRAMMAR_REVIEW_SPEC)
