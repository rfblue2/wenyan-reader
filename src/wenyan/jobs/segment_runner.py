from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol, cast

from pydantic import BaseModel

from wenyan.core.ports.artifact_ref import (
    ArtifactRef,
    ParagraphArtifactKind,
    ParagraphRef,
    SegmentArtifactKind,
    SegmentRef,
)
from wenyan.core.run.segment_pipeline import invalidate_segment_review
from wenyan.jobs.context import JobContext, JobOptions
from wenyan_models.artifacts.paragraph import ParagraphDraft
from wenyan_models.artifacts.segment import TokenizationArtifact, TokenizationReviewArtifact
from wenyan_models.domain.enums import ComponentKind, ReviewStatus
from wenyan_models.domain.ids import ContentHash, DocumentId, SegmentId, segment_id
from wenyan_models.domain.results import JobFailure, JobOutcome, Promoted, Skipped
from wenyan_models.domain.targets import ParagraphBatch, SegmentTarget, SingleSegment

type SegmentOneRunner[T] = Callable[
    [JobContext, DocumentId, SegmentId, JobOptions],
    JobOutcome[T],
]

type SegmentJobPrepareResult = JobFailure | tuple[ContentHash, dict[str, str]]
type SegmentJobPrepare = Callable[
    [JobContext, DocumentId, SegmentId, JobOptions],
    SegmentJobPrepareResult,
]
type SegmentAnnotatePostProcess[T: BaseModel] = Callable[
    [T, JobContext, DocumentId, SegmentId, ContentHash],
    T,
]
type SegmentReviewPostWrite[T: BaseModel] = Callable[
    [JobContext, DocumentId, SegmentId, T, JobOptions],
    None,
]


class HasInputHash(Protocol):
    input_hash: ContentHash


class HasReviewStatus(Protocol):
    status: ReviewStatus


def resolve_segment_ids(
    ctx: JobContext,
    document_id: DocumentId,
    target: SegmentTarget,
) -> list[SegmentId]:
    match target:
        case SingleSegment(segment_id=segment_id_value):
            return [segment_id_value]
        case ParagraphBatch(paragraph_id=paragraph_id_value):
            draft_ref = ParagraphRef(ParagraphArtifactKind.DRAFT, document_id, paragraph_id_value)
            if not ctx.artifacts.exists(draft_ref):
                return []
            draft = ctx.artifacts.read(draft_ref, ParagraphDraft)
            return [segment_id(str(segment.id)) for segment in draft.segments]
    return []


def load_approved_tokenization_review(
    ctx: JobContext,
    document_id: DocumentId,
    segment_id_value: SegmentId,
    *,
    missing_review_message: str,
    blocked_message: str,
) -> JobFailure | tuple[TokenizationArtifact, TokenizationReviewArtifact]:
    tokenization_ref = SegmentRef(SegmentArtifactKind.TOKENIZATION, document_id, segment_id_value)
    if not ctx.artifacts.exists(tokenization_ref):
        return JobFailure(code="missing-input", message="tokenization artifact is missing")
    tokenization = ctx.artifacts.read(tokenization_ref, TokenizationArtifact)
    review_ref = SegmentRef(SegmentArtifactKind.TOKENIZATION_REVIEW, document_id, segment_id_value)
    if not ctx.artifacts.exists(review_ref):
        return JobFailure(code="missing-input", message=missing_review_message)
    review = ctx.artifacts.read(review_ref, TokenizationReviewArtifact)
    if review.status != ReviewStatus.APPROVED:
        return JobFailure(code="blocked-upstream", message=blocked_message)
    return tokenization, review


def stamp_segment_metadata[T: BaseModel](
    artifact: T,
    *,
    segment_id_value: SegmentId,
    input_hash: ContentHash,
    model: str,
) -> T:
    return artifact.model_copy(
        update={
            "segment_id": segment_id_value,
            "input_hash": input_hash,
            "model": model,
            "attempts": 1,
        },
    )


def skip_if_current[T: BaseModel](
    ctx: JobContext,
    ref: ArtifactRef,
    input_hash: ContentHash,
    model: type[T],
    options: JobOptions,
    *,
    reason: str,
) -> Skipped | None:
    if ctx.artifacts.exists(ref) and not options.force:
        existing = cast(HasInputHash, ctx.artifacts.read(ref, model))
        if existing.input_hash == input_hash:
            return Skipped(reason=reason)
    return None


def run_segment_batch[T](
    ctx: JobContext,
    document_id: DocumentId,
    target: SegmentTarget,
    options: JobOptions,
    *,
    empty_message: str,
    all_skipped_reason: str,
    run_one: SegmentOneRunner[T],
) -> JobOutcome[T]:
    segment_ids = resolve_segment_ids(ctx, document_id, target)
    if not segment_ids:
        return JobFailure(code="missing-segment", message=empty_message)
    last: T | None = None
    for segment_id_value in segment_ids:
        outcome = run_one(ctx, document_id, segment_id_value, options)
        match outcome:
            case JobFailure():
                return outcome
            case Skipped():
                continue
            case Promoted(artifact=artifact):
                last = artifact
    if last is None:
        return Skipped(reason=all_skipped_reason)
    return Promoted(artifact=last)


@dataclass(frozen=True)
class SegmentAnnotateJobSpec[T: BaseModel]:
    prompt_name: str
    output_model: type[T]
    artifact_kind: SegmentArtifactKind
    component_kind: ComponentKind
    skip_reason: str
    prepare: SegmentJobPrepare
    post_process: SegmentAnnotatePostProcess[T] | None = None


@dataclass(frozen=True)
class SegmentReviewJobSpec[T: BaseModel]:
    prompt_name: str
    output_model: type[T]
    review_kind: SegmentArtifactKind
    skip_reason: str
    reject_message: str
    prepare: SegmentJobPrepare
    post_write: SegmentReviewPostWrite[T] | None = None


def run_segment_annotate_job[T: BaseModel](
    ctx: JobContext,
    document_id: DocumentId,
    segment_id_value: SegmentId,
    options: JobOptions,
    spec: SegmentAnnotateJobSpec[T],
) -> JobOutcome[T]:
    prepared = spec.prepare(ctx, document_id, segment_id_value, options)
    if isinstance(prepared, JobFailure):
        return prepared
    input_hash, context = prepared
    artifact_ref = SegmentRef(spec.artifact_kind, document_id, segment_id_value)
    if skip := skip_if_current(
        ctx,
        artifact_ref,
        input_hash,
        spec.output_model,
        options,
        reason=spec.skip_reason,
    ):
        return skip
    prompt = ctx.prompts.build_prompt(spec.prompt_name, context)
    artifact = ctx.llm.complete_model(prompt, spec.output_model)
    if spec.post_process is not None:
        artifact = spec.post_process(artifact, ctx, document_id, segment_id_value, input_hash)
    artifact = stamp_segment_metadata(
        artifact,
        segment_id_value=segment_id_value,
        input_hash=input_hash,
        model=ctx.config.models.active_model,
    )
    if options.dry_run:
        return Promoted(artifact=artifact)
    invalidate_segment_review(
        ctx.artifacts,
        document_id,
        segment_id_value,
        spec.component_kind,
        dry_run=False,
    )
    ctx.artifacts.write(artifact_ref, artifact, dry_run=False)
    return Promoted(artifact=artifact)


def run_segment_review_job[T: BaseModel](
    ctx: JobContext,
    document_id: DocumentId,
    segment_id_value: SegmentId,
    options: JobOptions,
    spec: SegmentReviewJobSpec[T],
) -> JobOutcome[T]:
    prepared = spec.prepare(ctx, document_id, segment_id_value, options)
    if isinstance(prepared, JobFailure):
        return prepared
    input_hash, context = prepared
    review_ref = SegmentRef(spec.review_kind, document_id, segment_id_value)
    if skip := skip_if_current(
        ctx,
        review_ref,
        input_hash,
        spec.output_model,
        options,
        reason=spec.skip_reason,
    ):
        return skip
    prompt = ctx.prompts.build_prompt(spec.prompt_name, context)
    review = ctx.llm.complete_model(prompt, spec.output_model)
    review = stamp_segment_metadata(
        review,
        segment_id_value=segment_id_value,
        input_hash=input_hash,
        model=ctx.config.models.active_model,
    )
    if options.dry_run:
        return Promoted(artifact=review)
    ctx.artifacts.write(review_ref, review, dry_run=False)
    if cast(HasReviewStatus, review).status == ReviewStatus.REJECTED:
        return JobFailure(code="review-rejected", message=spec.reject_message)
    if spec.post_write is not None:
        spec.post_write(ctx, document_id, segment_id_value, review, options)
    return Promoted(artifact=review)
