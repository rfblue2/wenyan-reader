from wenyan.core.adapters.hashing import sha256_text
from wenyan.core.adapters.prompt_template import RenderedPrompt, load_prompt_template
from wenyan.core.ports.artifact_ref import segment_input_ref, segment_tokenization_ref
from wenyan.core.run.segment_pipeline import invalidate_segment_review
from wenyan.jobs.context import JobContext, JobOptions
from wenyan_models.artifacts.segment import SegmentInput, TokenizationArtifact
from wenyan_models.text.tokenization import drop_punctuation_tokens
from wenyan_models.domain.enums import ComponentKind
from wenyan_models.domain.ids import DocumentId, SegmentId, segment_id
from wenyan_models.domain.results import JobFailure, JobOutcome, Promoted, Skipped
from wenyan_models.domain.targets import ParagraphBatch, SegmentTarget, SingleSegment


def run_tokenize_segment(
    ctx: JobContext,
    document_id: DocumentId,
    target: SegmentTarget,
    options: JobOptions,
) -> JobOutcome[TokenizationArtifact]:
    segment_ids = _resolve_segment_ids(ctx, document_id, target)
    if not segment_ids:
        return JobFailure(code="missing-segment", message="no segments to tokenize")
    last: TokenizationArtifact | None = None
    for segment_id_value in segment_ids:
        outcome = _tokenize_one(ctx, document_id, segment_id_value, options)
        match outcome:
            case JobFailure():
                return outcome
            case Skipped():
                continue
            case Promoted(artifact=artifact):
                last = artifact
    if last is None:
        return Skipped(reason="all segments already tokenized")
    return Promoted(artifact=last)


def _tokenize_one(
    ctx: JobContext,
    document_id: DocumentId,
    segment_id_value: SegmentId,
    options: JobOptions,
) -> JobOutcome[TokenizationArtifact]:
    input_ref = segment_input_ref(document_id, segment_id_value)
    if not ctx.artifacts.exists(input_ref):
        return JobFailure(code="missing-input", message="segment input is missing")
    segment_input = ctx.artifacts.read(input_ref, SegmentInput)
    tokenization_ref = segment_tokenization_ref(document_id, segment_id_value)
    input_hash = sha256_text(segment_input.segment_text)
    if ctx.artifacts.exists(tokenization_ref) and not options.force:
        existing = ctx.artifacts.read(tokenization_ref, TokenizationArtifact)
        if existing.input_hash == input_hash:
            return Skipped(reason="tokenization is current")
    template = load_prompt_template(
        ctx.repo_root / ctx.config.prompts.root,
        "segment-tokenization",
    )
    context = {
        "segment_text": segment_input.segment_text,
        "segment_id": str(segment_id_value),
        "input_hash": str(input_hash),
    }
    tokenization = ctx.llm.complete_model(RenderedPrompt(template, context), TokenizationArtifact)
    tokenization = tokenization.model_copy(
        update={
            "segment_id": segment_id_value,
            "input_hash": input_hash,
            "model": ctx.config.models.active_model,
            "attempts": 1,
            "tokens": drop_punctuation_tokens(tokenization.tokens),
        },
    )
    if options.dry_run:
        return Promoted(artifact=tokenization)
    invalidate_segment_review(
        ctx.artifacts,
        document_id,
        segment_id_value,
        ComponentKind.TOKENIZE_SEGMENT,
        dry_run=False,
    )
    ctx.artifacts.write(tokenization_ref, tokenization, dry_run=False)
    return Promoted(artifact=tokenization)


def _resolve_segment_ids(
    ctx: JobContext,
    document_id: DocumentId,
    target: SegmentTarget,
) -> list[SegmentId]:
    match target:
        case SingleSegment(segment_id=segment_id_value):
            return [segment_id_value]
        case ParagraphBatch(paragraph_id=paragraph_id_value):
            from wenyan.core.ports.artifact_ref import paragraph_draft_ref
            from wenyan_models.artifacts.paragraph import ParagraphDraft

            draft_ref = paragraph_draft_ref(document_id, paragraph_id_value)
            if not ctx.artifacts.exists(draft_ref):
                return []
            draft = ctx.artifacts.read(draft_ref, ParagraphDraft)
            return [segment_id(str(segment.id)) for segment in draft.segments]
    return []
