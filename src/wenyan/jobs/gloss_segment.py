from wenyan.core.gloss.glossary_draft import (
    load_candidate_glosses,
    normalize_gloss_reuse,
)
import json

from wenyan.core.adapters.hashing import sha256_text
from wenyan.core.adapters.prompt_template import RenderedPrompt, load_prompt_template
from wenyan.core.ports.artifact_ref import (
    segment_glosses_ref,
    segment_input_ref,
    segment_tokenization_ref,
    segment_tokenization_review_ref,
)
from wenyan.jobs.context import JobContext, JobOptions
from wenyan_models.artifacts.segment import (
    GlossEntry,
    GlossesArtifact,
    SegmentInput,
    TokenizationArtifact,
    TokenizationReviewArtifact,
)
from wenyan_models.domain.enums import ReviewStatus
from wenyan_models.domain.ids import DocumentId, SegmentId, segment_id
from wenyan_models.domain.results import JobFailure, JobOutcome, Promoted, Skipped
from wenyan_models.domain.targets import ParagraphBatch, SegmentTarget, SingleSegment


def run_gloss_segment(
    ctx: JobContext,
    document_id: DocumentId,
    target: SegmentTarget,
    options: JobOptions,
) -> JobOutcome[GlossesArtifact]:
    segment_ids = _resolve_segment_ids(ctx, document_id, target)
    if not segment_ids:
        return JobFailure(code="missing-segment", message="no segments to gloss")
    last: GlossesArtifact | None = None
    for segment_id_value in segment_ids:
        outcome = _gloss_one(ctx, document_id, segment_id_value, options)
        match outcome:
            case JobFailure():
                return outcome
            case Skipped():
                continue
            case Promoted(artifact=artifact):
                last = artifact
    if last is None:
        return Skipped(reason="all segments already glossed")
    return Promoted(artifact=last)


def _gloss_one(
    ctx: JobContext,
    document_id: DocumentId,
    segment_id_value: SegmentId,
    options: JobOptions,
) -> JobOutcome[GlossesArtifact]:
    upstream = _load_approved_tokenization_review(ctx, document_id, segment_id_value)
    if isinstance(upstream, JobFailure):
        return upstream
    tokenization, tokenization_review = upstream
    input_ref = segment_input_ref(document_id, segment_id_value)
    if not ctx.artifacts.exists(input_ref):
        return JobFailure(code="missing-input", message="segment input is missing")
    segment_input = ctx.artifacts.read(input_ref, SegmentInput)
    glosses_ref = segment_glosses_ref(document_id, segment_id_value)
    input_hash = sha256_text(tokenization_review.model_dump_json(by_alias=True))
    if ctx.artifacts.exists(glosses_ref) and not options.force:
        existing = ctx.artifacts.read(glosses_ref, GlossesArtifact)
        if existing.input_hash == input_hash:
            return Skipped(reason="glosses are current")
    template = load_prompt_template(
        ctx.repo_root / ctx.config.prompts.root,
        "segment-gloss",
    )
    candidate_glosses = load_candidate_glosses(ctx.artifacts, document_id, segment_id_value)
    segment_candidates = tuple(
        GlossEntry.model_validate(dict(item)) for item in segment_input.candidate_glosses
    )
    all_candidates = _merge_gloss_entries(candidate_glosses, segment_candidates)
    context = {
        "segment_id": str(segment_id_value),
        "segment_text": tokenization.text,
        "input_hash": str(input_hash),
        "tokenization_json": tokenization.model_dump_json(by_alias=True),
        "candidate_glosses_json": json.dumps(
            [entry.model_dump(by_alias=True) for entry in all_candidates],
            ensure_ascii=False,
        ),
    }
    glosses = ctx.llm.complete_model(RenderedPrompt(template, context), GlossesArtifact)
    glosses = normalize_gloss_reuse(glosses, tokenization, all_candidates)
    glosses = glosses.model_copy(
        update={
            "segment_id": segment_id_value,
            "input_hash": input_hash,
            "model": ctx.config.models.active_model,
            "attempts": 1,
        },
    )
    if options.dry_run:
        return Promoted(artifact=glosses)
    ctx.artifacts.write(glosses_ref, glosses, dry_run=False)
    return Promoted(artifact=glosses)


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
            message="approved tokenization review is required before glossing",
        )
    review = ctx.artifacts.read(review_ref, TokenizationReviewArtifact)
    if review.status != ReviewStatus.APPROVED:
        return JobFailure(
            code="blocked-upstream",
            message="tokenization review must be approved before glossing",
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
            from wenyan.core.ports.artifact_ref import paragraph_draft_ref
            from wenyan_models.artifacts.paragraph import ParagraphDraft

            draft_ref = paragraph_draft_ref(document_id, paragraph_id_value)
            if not ctx.artifacts.exists(draft_ref):
                return []
            draft = ctx.artifacts.read(draft_ref, ParagraphDraft)
            return [segment_id(str(segment.id)) for segment in draft.segments]
    return []


def _merge_gloss_entries(
    *groups: tuple[GlossEntry, ...],
) -> tuple[GlossEntry, ...]:
    by_id: dict[str, GlossEntry] = {}
    for group in groups:
        for entry in group:
            by_id[entry.id] = entry
    return tuple(by_id.values())
