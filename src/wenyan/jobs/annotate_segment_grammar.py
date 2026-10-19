from wenyan.core.hashing import sha256_text
from wenyan.core.notes.normalize_notes import normalize_grammar_notes
from wenyan.core.ports.artifact_ref import SegmentArtifactKind, SegmentRef
from wenyan.core.run.segment_pipeline import GRAMMAR_STAGE
from wenyan.jobs.context import JobContext, JobOptions
from wenyan.jobs.segment_runner import (
    Prepared,
    SegmentAnnotateJobSpec,
    load_approved_tokenization_review,
    run_segment_job,
)
from wenyan_models.artifacts.segment import GrammarNotesArtifact, SegmentInput, TokenizationArtifact
from wenyan_models.domain.ids import DocumentId, SegmentId
from wenyan_models.domain.results import JobFailure, JobOutcome
from wenyan_models.domain.targets import SegmentTarget


def _prepare_grammar(
    ctx: JobContext,
    document_id: DocumentId,
    segment_id_value: SegmentId,
) -> JobFailure | Prepared:
    upstream = load_approved_tokenization_review(
        ctx,
        document_id,
        segment_id_value,
        missing_review_message="approved tokenization review is required before grammar annotation",
        blocked_message="tokenization review must be approved before grammar annotation",
    )
    if isinstance(upstream, JobFailure):
        return upstream
    tokenization, tokenization_review = upstream
    input_ref = SegmentRef(SegmentArtifactKind.INPUT, document_id, segment_id_value)
    if not ctx.artifacts.exists(input_ref):
        return JobFailure(code="missing-input", message="segment input is missing")
    segment_input = ctx.artifacts.read(input_ref, SegmentInput)
    input_hash = sha256_text(tokenization_review.model_dump_json(by_alias=True))
    context = {
        "segment_id": str(segment_id_value),
        "segment_text": tokenization.text,
        "input_hash": str(input_hash),
        "tokenization_json": tokenization.model_dump_json(by_alias=True),
        "local_context_json": segment_input.local_context.model_dump_json(by_alias=True),
    }
    return Prepared(input_hash, context)


def _post_process_grammar(
    grammar_notes: GrammarNotesArtifact,
    ctx: JobContext,
    document_id: DocumentId,
    segment_id_value: SegmentId,
) -> GrammarNotesArtifact:
    tokenization = ctx.artifacts.read(
        SegmentRef(SegmentArtifactKind.TOKENIZATION, document_id, segment_id_value),
        TokenizationArtifact,
    )
    return grammar_notes.model_copy(
        update={
            "grammar_notes": normalize_grammar_notes(
                grammar_notes.grammar_notes,
                tokenization,
            ),
        },
    )


_GRAMMAR_SPEC = SegmentAnnotateJobSpec(
    stage=GRAMMAR_STAGE,
    prompt_name="segment-grammar",
    output_model=GrammarNotesArtifact,
    prepare=_prepare_grammar,
    post_process=_post_process_grammar,
    empty_message="no segments to annotate",
    skip_reason="all segments already have current grammar notes",
)


def run_annotate_segment_grammar(
    ctx: JobContext,
    document_id: DocumentId,
    target: SegmentTarget,
    options: JobOptions,
) -> JobOutcome[GrammarNotesArtifact]:
    return run_segment_job(ctx, document_id, target, options, _GRAMMAR_SPEC)
