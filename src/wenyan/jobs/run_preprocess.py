from typing import Any

from pydantic import BaseModel

from wenyan.core.run.segment_pipeline import pending_segment_subjobs
from wenyan.core.run.work_queue import (
    find_next_paragraph_needing_split_segments,
    find_next_segment_work,
)
from wenyan.jobs.context import JobContext, JobOptions
from wenyan.jobs.annotate_segment_context import run_annotate_segment_context
from wenyan.jobs.annotate_segment_grammar import run_annotate_segment_grammar
from wenyan.jobs.gloss_segment import run_gloss_segment
from wenyan.jobs.review_segment_context import run_review_segment_context
from wenyan.jobs.review_segment_gloss import run_review_segment_gloss
from wenyan.jobs.review_segment_grammar import run_review_segment_grammar
from wenyan.jobs.review_segment_tokenization import run_review_segment_tokenization
from wenyan.jobs.segment_runner import SegmentJob
from wenyan.jobs.split_segments import run_split_segments
from wenyan.jobs.tokenize_segment import run_tokenize_segment
from wenyan_models.base import DEFAULT_ARTIFACT_CONFIG
from wenyan_models.domain.enums import ComponentKind
from wenyan_models.domain.ids import DocumentId, ParagraphId, SegmentId
from wenyan_models.domain.results import JobFailure, JobOutcome, Promoted, Skipped, outcome_exit_code
from wenyan_models.domain.targets import SingleSegment


_SEGMENT_JOBS: dict[ComponentKind, SegmentJob[Any]] = {
    ComponentKind.TOKENIZE_SEGMENT: run_tokenize_segment,
    ComponentKind.REVIEW_SEGMENT_TOKENIZATION: run_review_segment_tokenization,
    ComponentKind.GLOSS_SEGMENT: run_gloss_segment,
    ComponentKind.REVIEW_SEGMENT_GLOSS: run_review_segment_gloss,
    ComponentKind.ANNOTATE_SEGMENT_GRAMMAR: run_annotate_segment_grammar,
    ComponentKind.REVIEW_SEGMENT_GRAMMAR: run_review_segment_grammar,
    ComponentKind.ANNOTATE_SEGMENT_CONTEXT: run_annotate_segment_context,
    ComponentKind.REVIEW_SEGMENT_CONTEXT: run_review_segment_context,
}


class RunPlan(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    document_id: DocumentId
    stages_run: tuple[str, ...] = ()
    segment_id: SegmentId | None = None
    paragraph_id: ParagraphId | None = None
    text_preview: str = ""


def run_preprocess(
    ctx: JobContext,
    document_id: DocumentId,
    *,
    segment_id_value: SegmentId | None = None,
    next_segment: bool = False,
    next_paragraph: bool = False,
    options: JobOptions,
) -> JobOutcome[RunPlan]:
    if next_paragraph:
        if segment_id_value is not None or next_segment:
            return JobFailure(
                code="invalid-target",
                message="use only one of --next-paragraph, --next-segment, or --segment",
            )
        return _run_next_paragraph(ctx, document_id, options)
    if segment_id_value is not None:
        if next_segment:
            return JobFailure(
                code="invalid-target",
                message="use only one of --next-segment or --segment",
            )
        return _run_segment(ctx, document_id, segment_id_value, options)
    return _run_next_segment(ctx, document_id, options)


def _run_next_paragraph(
    ctx: JobContext,
    document_id: DocumentId,
    options: JobOptions,
) -> JobOutcome[RunPlan]:
    work = find_next_paragraph_needing_split_segments(ctx.artifacts, document_id)
    if work is None:
        return Skipped(reason="all paragraphs already have segment drafts")
    outcome = run_split_segments(ctx, document_id, work.paragraph_id, options)
    if outcome_exit_code(outcome) != 0:
        return _failure_from_outcome(["split-segments"], outcome)
    return Promoted(
        artifact=RunPlan(
            document_id=document_id,
            stages_run=("split-segments",),
            paragraph_id=work.paragraph_id,
            text_preview=work.text_preview,
        ),
    )


def _run_next_segment(
    ctx: JobContext,
    document_id: DocumentId,
    options: JobOptions,
) -> JobOutcome[RunPlan]:
    while True:
        work = find_next_segment_work(ctx.artifacts, document_id)
        if work is None:
            return Skipped(reason="no segments pending preprocessing")
        if work.segment_id is None:
            outcome = run_split_segments(ctx, document_id, work.paragraph_id, options)
            if outcome_exit_code(outcome) != 0:
                return _failure_from_outcome(["split-segments"], outcome)
            continue
        return _run_segment(
            ctx,
            document_id,
            work.segment_id,
            options,
            text_preview=work.text_preview,
        )


def _run_segment(
    ctx: JobContext,
    document_id: DocumentId,
    segment_id_value: SegmentId,
    options: JobOptions,
    *,
    text_preview: str = "",
) -> JobOutcome[RunPlan]:
    stages_run: list[str] = []
    for component in pending_segment_subjobs(ctx.artifacts, document_id, segment_id_value):
        target = SingleSegment(segment_id=segment_id_value)
        outcome = _SEGMENT_JOBS[component](ctx, document_id, target, options)
        stages_run.append(component.value)
        if outcome_exit_code(outcome) != 0:
            return _failure_from_outcome(stages_run, outcome)
    if not stages_run:
        return Skipped(reason="segment is already complete")
    return Promoted(
        artifact=RunPlan(
            document_id=document_id,
            stages_run=tuple(stages_run),
            segment_id=segment_id_value,
            text_preview=text_preview,
        ),
    )


def _failure_from_outcome[T](
    stages_run: list[str],
    outcome: JobOutcome[T],
) -> JobFailure:
    match outcome:
        case JobFailure(code=code, message=message):
            return JobFailure(
                code=code,
                message=f"stopped after {', '.join(stages_run) or 'no stages'}: {message}",
            )
        case _:
            return JobFailure(
                code="run-failed",
                message=f"stopped after {', '.join(stages_run) or 'no stages'}",
            )
