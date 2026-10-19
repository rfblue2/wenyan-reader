from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from wenyan.core.ports.artifact_ref import (
    ParagraphArtifactKind,
    ParagraphRef,
    SegmentArtifactKind,
    SegmentRef,
)
from wenyan.core.run.segment_pipeline import SegmentStage
from wenyan.jobs.context import JobContext, JobOptions
from wenyan_models.artifacts.paragraph import ParagraphDraft
from wenyan_models.artifacts.segment import SegmentArtifact, SegmentReview, TokenizationArtifact
from wenyan_models.domain.enums import ReviewStatus
from wenyan_models.domain.ids import ContentHash, DocumentId, SegmentId, segment_id
from wenyan_models.domain.results import JobFailure, JobOutcome, Promoted, Skipped
from wenyan_models.domain.targets import ParagraphBatch, SegmentTarget, SingleSegment

type SegmentJob[T] = Callable[[JobContext, DocumentId, SegmentTarget, JobOptions], JobOutcome[T]]


@dataclass(frozen=True)
class Prepared:
    input_hash: ContentHash
    context: dict[str, str]


type Prepare = Callable[[JobContext, DocumentId, SegmentId], JobFailure | Prepared]


class SegmentJobSpec[T](Protocol):
    @property
    def empty_message(self) -> str: ...

    @property
    def skip_reason(self) -> str: ...

    def run_one(
        self,
        ctx: JobContext,
        document_id: DocumentId,
        segment_id_value: SegmentId,
        options: JobOptions,
    ) -> JobOutcome[T]: ...


@dataclass(frozen=True, kw_only=True)
class SegmentAnnotateJobSpec[T: SegmentArtifact]:
    stage: SegmentStage
    prompt_name: str
    output_model: type[T]
    prepare: Prepare
    post_process: Callable[[T, JobContext, DocumentId, SegmentId], T] | None = None
    empty_message: str
    skip_reason: str

    def run_one(
        self,
        ctx: JobContext,
        document_id: DocumentId,
        segment_id_value: SegmentId,
        options: JobOptions,
    ) -> JobOutcome[T]:
        prepared = self.prepare(ctx, document_id, segment_id_value)
        if isinstance(prepared, JobFailure):
            return prepared
        ref = SegmentRef(self.stage.draft_kind, document_id, segment_id_value)
        if _is_current(ctx, ref, self.output_model, prepared.input_hash, options):
            return Skipped(reason=self.skip_reason)
        artifact = _complete(ctx, self.prompt_name, self.output_model, prepared, segment_id_value)
        if self.post_process is not None:
            artifact = self.post_process(artifact, ctx, document_id, segment_id_value)
        if options.dry_run:
            return Promoted(artifact=artifact)
        review_ref = SegmentRef(self.stage.review_kind, document_id, segment_id_value)
        if ctx.artifacts.exists(review_ref):
            ctx.artifacts.delete(review_ref)
        ctx.artifacts.write(ref, artifact, dry_run=False)
        return Promoted(artifact=artifact)


@dataclass(frozen=True, kw_only=True)
class SegmentReviewJobSpec:
    stage: SegmentStage
    prompt_name: str
    prepare: Prepare
    post_write: Callable[[JobContext, DocumentId, SegmentId], None] | None = None
    empty_message: str
    skip_reason: str
    reject_message: str

    def run_one(
        self,
        ctx: JobContext,
        document_id: DocumentId,
        segment_id_value: SegmentId,
        options: JobOptions,
    ) -> JobOutcome[SegmentReview]:
        prepared = self.prepare(ctx, document_id, segment_id_value)
        if isinstance(prepared, JobFailure):
            return prepared
        ref = SegmentRef(self.stage.review_kind, document_id, segment_id_value)
        if _is_current(ctx, ref, self.stage.review_model, prepared.input_hash, options):
            return Skipped(reason=self.skip_reason)
        review = _complete(ctx, self.prompt_name, self.stage.review_model, prepared, segment_id_value)
        if options.dry_run:
            return Promoted(artifact=review)
        ctx.artifacts.write(ref, review, dry_run=False)
        if review.status == ReviewStatus.REJECTED:
            return JobFailure(code="review-rejected", message=self.reject_message)
        if self.post_write is not None:
            self.post_write(ctx, document_id, segment_id_value)
        return Promoted(artifact=review)


def run_segment_job[T](
    ctx: JobContext,
    document_id: DocumentId,
    target: SegmentTarget,
    options: JobOptions,
    spec: SegmentJobSpec[T],
) -> JobOutcome[T]:
    segment_ids = _resolve_segment_ids(ctx, document_id, target)
    if not segment_ids:
        return JobFailure(code="missing-segment", message=spec.empty_message)
    last: T | None = None
    for segment_id_value in segment_ids:
        outcome = spec.run_one(ctx, document_id, segment_id_value, options)
        match outcome:
            case JobFailure():
                return outcome
            case Skipped():
                continue
            case Promoted(artifact=artifact):
                last = artifact
    if last is None:
        return Skipped(reason=spec.skip_reason)
    return Promoted(artifact=last)


def load_approved_tokenization_review(
    ctx: JobContext,
    document_id: DocumentId,
    segment_id_value: SegmentId,
    *,
    missing_review_message: str,
    blocked_message: str,
) -> JobFailure | tuple[TokenizationArtifact, SegmentReview]:
    tokenization_ref = SegmentRef(SegmentArtifactKind.TOKENIZATION, document_id, segment_id_value)
    if not ctx.artifacts.exists(tokenization_ref):
        return JobFailure(code="missing-input", message="tokenization artifact is missing")
    tokenization = ctx.artifacts.read(tokenization_ref, TokenizationArtifact)
    review_ref = SegmentRef(SegmentArtifactKind.TOKENIZATION_REVIEW, document_id, segment_id_value)
    if not ctx.artifacts.exists(review_ref):
        return JobFailure(code="missing-input", message=missing_review_message)
    review = ctx.artifacts.read(review_ref, SegmentReview)
    if review.status != ReviewStatus.APPROVED:
        return JobFailure(code="blocked-upstream", message=blocked_message)
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
            draft_ref = ParagraphRef(ParagraphArtifactKind.DRAFT, document_id, paragraph_id_value)
            if not ctx.artifacts.exists(draft_ref):
                return []
            draft = ctx.artifacts.read(draft_ref, ParagraphDraft)
            return [segment_id(str(segment.id)) for segment in draft.segments]


def _is_current[T: SegmentArtifact](
    ctx: JobContext,
    ref: SegmentRef,
    model: type[T],
    input_hash: ContentHash,
    options: JobOptions,
) -> bool:
    if options.force or not ctx.artifacts.exists(ref):
        return False
    return ctx.artifacts.read(ref, model).input_hash == input_hash


def _complete[T: SegmentArtifact](
    ctx: JobContext,
    prompt_name: str,
    model: type[T],
    prepared: Prepared,
    segment_id_value: SegmentId,
) -> T:
    prompt = ctx.prompts.build_prompt(prompt_name, prepared.context)
    return stamp_segment_metadata(
        ctx.llm.complete_model(prompt, model),
        segment_id_value=segment_id_value,
        input_hash=prepared.input_hash,
        model=ctx.config.models.active_model,
    )


def stamp_segment_metadata[T: SegmentArtifact](
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
