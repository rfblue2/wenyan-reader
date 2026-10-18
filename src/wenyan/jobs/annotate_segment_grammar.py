from wenyan.core.hashing import sha256_text
from wenyan.core.notes.normalize_notes import normalize_grammar_notes
from wenyan.core.ports.artifact_ref import (
    segment_grammar_notes_ref,
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
from wenyan_models.artifacts.segment import GrammarNotesArtifact, SegmentInput, TokenizationArtifact
from wenyan_models.domain.enums import ComponentKind
from wenyan_models.domain.ids import ContentHash, DocumentId, SegmentId
from wenyan_models.domain.results import JobFailure, JobOutcome
from wenyan_models.domain.targets import SegmentTarget


def _prepare_grammar(
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
        missing_review_message="approved tokenization review is required before grammar annotation",
        blocked_message="tokenization review must be approved before grammar annotation",
    )
    if isinstance(upstream, JobFailure):
        return upstream
    tokenization, tokenization_review = upstream
    input_ref = segment_input_ref(document_id, segment_id_value)
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
    return input_hash, context


def _post_process_grammar(
    grammar_notes: GrammarNotesArtifact,
    ctx: JobContext,
    document_id: DocumentId,
    segment_id_value: SegmentId,
    input_hash: ContentHash,
) -> GrammarNotesArtifact:
    del input_hash
    tokenization = ctx.artifacts.read(
        segment_tokenization_ref(document_id, segment_id_value),
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
    prompt_name="segment-grammar",
    output_model=GrammarNotesArtifact,
    artifact_ref=segment_grammar_notes_ref,
    component_kind=ComponentKind.ANNOTATE_SEGMENT_GRAMMAR,
    skip_reason="grammar notes are current",
    prepare=_prepare_grammar,
    post_process=_post_process_grammar,
)


def run_annotate_segment_grammar(
    ctx: JobContext,
    document_id: DocumentId,
    target: SegmentTarget,
    options: JobOptions,
) -> JobOutcome[GrammarNotesArtifact]:
    return run_segment_batch(
        ctx,
        document_id,
        target,
        options,
        empty_message="no segments to annotate",
        all_skipped_reason="all segments already have current grammar notes",
        run_one=_annotate_one,
    )


def _annotate_one(
    ctx: JobContext,
    document_id: DocumentId,
    segment_id_value: SegmentId,
    options: JobOptions,
) -> JobOutcome[GrammarNotesArtifact]:
    return run_segment_annotate_job(ctx, document_id, segment_id_value, options, _GRAMMAR_SPEC)
