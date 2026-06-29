import json

from wenyan.core.adapters.hashing import sha256_text
from wenyan.core.adapters.prompt_template import RenderedPrompt, load_prompt_template
from wenyan.core.notes.normalize_notes import normalize_notes
from wenyan.core.ports.artifact_ref import (
    paragraph_draft_ref,
    segment_context_notes_ref,
    segment_input_ref,
    segment_tokenization_ref,
    segment_tokenization_review_ref,
)
from wenyan.jobs.context import JobContext, JobOptions
from wenyan_models.artifacts.paragraph import ParagraphDraft
from wenyan_models.artifacts.segment import (
    ContextNotesArtifact,
    SegmentInput,
    TokenizationArtifact,
    TokenizationReviewArtifact,
)
from wenyan_models.domain.enums import ReviewStatus
from wenyan_models.domain.ids import DocumentId, SegmentId, segment_id
from wenyan_models.domain.results import JobFailure, JobOutcome, Promoted, Skipped
from wenyan_models.domain.targets import ParagraphBatch, SegmentTarget, SingleSegment


def run_annotate_segment_context(
    ctx: JobContext,
    document_id: DocumentId,
    target: SegmentTarget,
    options: JobOptions,
) -> JobOutcome[ContextNotesArtifact]:
    segment_ids = _resolve_segment_ids(ctx, document_id, target)
    if not segment_ids:
        return JobFailure(code="missing-segment", message="no segments to annotate")
    last: ContextNotesArtifact | None = None
    for segment_id_value in segment_ids:
        outcome = _annotate_one(ctx, document_id, segment_id_value, options)
        match outcome:
            case JobFailure():
                return outcome
            case Skipped():
                continue
            case Promoted(artifact=artifact):
                last = artifact
    if last is None:
        return Skipped(reason="all segments already have current context notes")
    return Promoted(artifact=last)


def _annotate_one(
    ctx: JobContext,
    document_id: DocumentId,
    segment_id_value: SegmentId,
    options: JobOptions,
) -> JobOutcome[ContextNotesArtifact]:
    upstream = _load_approved_tokenization_review(ctx, document_id, segment_id_value)
    if isinstance(upstream, JobFailure):
        return upstream
    tokenization, tokenization_review = upstream
    input_ref = segment_input_ref(document_id, segment_id_value)
    if not ctx.artifacts.exists(input_ref):
        return JobFailure(code="missing-input", message="segment input is missing")
    segment_input = ctx.artifacts.read(input_ref, SegmentInput)
    context_ref = segment_context_notes_ref(document_id, segment_id_value)
    input_hash = sha256_text(tokenization_review.model_dump_json(by_alias=True))
    if ctx.artifacts.exists(context_ref) and not options.force:
        existing = ctx.artifacts.read(context_ref, ContextNotesArtifact)
        if existing.input_hash == input_hash:
            return Skipped(reason="context notes are current")
    template = load_prompt_template(
        ctx.repo_root / ctx.config.prompts.root,
        "segment-context",
    )
    source_snippet_ids = _source_snippet_ids(segment_input)
    context = {
        "segment_id": str(segment_id_value),
        "segment_text": tokenization.text,
        "input_hash": str(input_hash),
        "tokenization_json": tokenization.model_dump_json(by_alias=True),
        "local_context_json": json.dumps(segment_input.local_context, ensure_ascii=False),
        "source_snippets_json": json.dumps(
            [item for item in segment_input.source_snippets],
            ensure_ascii=False,
        ),
    }
    context_notes = ctx.llm.complete_model(RenderedPrompt(template, context), ContextNotesArtifact)
    context_notes = context_notes.model_copy(
        update={
            "context_notes": normalize_notes(
                context_notes.context_notes,
                tokenization,
                source_snippet_ids=source_snippet_ids,
            ),
        },
    )
    context_notes = context_notes.model_copy(
        update={
            "segment_id": segment_id_value,
            "input_hash": input_hash,
            "model": ctx.config.models.active_model,
            "attempts": 1,
        },
    )
    if options.dry_run:
        return Promoted(artifact=context_notes)
    ctx.artifacts.write(context_ref, context_notes, dry_run=False)
    return Promoted(artifact=context_notes)


def _load_approved_tokenization_review(
    ctx: JobContext,
    document_id: DocumentId,
    segment_id_value: SegmentId,
) -> JobFailure | tuple[TokenizationArtifact, TokenizationReviewArtifact]:
    tokenization_ref = segment_tokenization_ref(document_id, segment_id_value)
    if not ctx.artifacts.exists(tokenization_ref):
        return JobFailure(code="missing-input", message="tokenization artifact is missing")
    tokenization = ctx.artifacts.read(tokenization_ref, TokenizationArtifact)
    review_ref = segment_tokenization_review_ref(document_id, segment_id_value)
    if not ctx.artifacts.exists(review_ref):
        return JobFailure(
            code="missing-input",
            message="approved tokenization review is required before context annotation",
        )
    review = ctx.artifacts.read(review_ref, TokenizationReviewArtifact)
    if review.status != ReviewStatus.APPROVED:
        return JobFailure(
            code="blocked-upstream",
            message="tokenization review must be approved before context annotation",
        )
    return tokenization, review


def _resolve_segment_ids(
    ctx: JobContext,
    document_id: DocumentId,
    target: SegmentTarget,
) -> list[SegmentId]:
    match target:
        case SingleSegment(segment_id=segment_id_value):
            return [segment_id_value]
        case ParagraphBatch(paragraph_id=paragraph_id_value):
            draft_ref = paragraph_draft_ref(document_id, paragraph_id_value)
            if not ctx.artifacts.exists(draft_ref):
                return []
            draft = ctx.artifacts.read(draft_ref, ParagraphDraft)
            return [segment_id(str(segment.id)) for segment in draft.segments]
    return []


def _source_snippet_ids(segment_input: SegmentInput) -> frozenset[str] | None:
    ids = {
        str(item.get("id"))
        for item in segment_input.source_snippets
        if isinstance(item, dict) and item.get("id") is not None
    }
    if not ids:
        return None
    return frozenset(ids)
