from collections.abc import Callable

from pydantic import BaseModel, ConfigDict

from wenyan.core.run.segment_pipeline import pending_segment_subjobs
from wenyan.core.run.work_queue import (
    find_next_paragraph_needing_split_segments,
    find_next_segment_work,
)
from wenyan.jobs.context import JobContext, JobOptions
from wenyan.jobs.gloss_segment import run_gloss_segment
from wenyan.jobs.review_segment_gloss import run_review_segment_gloss
from wenyan.jobs.review_segment_tokenization import run_review_segment_tokenization
from wenyan.jobs.split_segments import run_split_segments
from wenyan.jobs.tokenize_segment import run_tokenize_segment
from wenyan_models.domain.enums import ComponentKind
from wenyan_models.domain.ids import DocumentId, ParagraphId, SegmentId
from wenyan_models.domain.results import JobFailure, JobOutcome, Promoted, Skipped, outcome_exit_code
from wenyan_models.domain.targets import single_segment_target

_DEFAULT_MODEL_CONFIG = {"frozen": True, "populate_by_name": True, "extra": "forbid"}

_IMPLEMENTED_SUBJOBS: dict[
    ComponentKind,
    Callable[[JobContext, DocumentId, SegmentId, JobOptions], JobOutcome[object]],
] = {
    ComponentKind.TOKENIZE_SEGMENT: lambda ctx, doc_id, segment_id, options: run_tokenize_segment(
        ctx,
        doc_id,
        single_segment_target(segment_id),
        options,
    ),
    ComponentKind.REVIEW_SEGMENT_TOKENIZATION: (
        lambda ctx, doc_id, segment_id, options: run_review_segment_tokenization(
            ctx,
            doc_id,
            segment_id,
            options,
        )
    ),
    ComponentKind.GLOSS_SEGMENT: lambda ctx, doc_id, segment_id, options: run_gloss_segment(
        ctx,
        doc_id,
        single_segment_target(segment_id),
        options,
    ),
    ComponentKind.REVIEW_SEGMENT_GLOSS: (
        lambda ctx, doc_id, segment_id, options: run_review_segment_gloss(
            ctx,
            doc_id,
            segment_id,
            options,
        )
    ),
}


class RunPlan(BaseModel):
    model_config = ConfigDict(**_DEFAULT_MODEL_CONFIG)

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
        return _failure_from_outcome(
            document_id,
            ["split-segments"],
            outcome,
            paragraph_id=work.paragraph_id,
        )
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
                return _failure_from_outcome(
                    document_id,
                    ["split-segments"],
                    outcome,
                    paragraph_id=work.paragraph_id,
                )
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
        runner = _IMPLEMENTED_SUBJOBS.get(component)
        if runner is None:
            return JobFailure(
                code="not-implemented",
                message=(
                    f"stopped after {', '.join(stages_run) or 'no stages'}: "
                    f"{component.value} is not implemented yet"
                ),
            )
        outcome = runner(ctx, document_id, segment_id_value, options)
        stages_run.append(component.value)
        if outcome_exit_code(outcome) != 0:
            return _failure_from_outcome(
                document_id,
                stages_run,
                outcome,
                segment_id=segment_id_value,
            )
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


def _failure_from_outcome(
    document_id: DocumentId,
    stages_run: list[str],
    outcome: JobOutcome[object],
    *,
    paragraph_id: ParagraphId | None = None,
    segment_id: SegmentId | None = None,
) -> JobFailure:
    del document_id, paragraph_id, segment_id
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
