from __future__ import annotations

from collections.abc import Callable
from typing import NoReturn, TypeVar

import typer

from wenyan.bootstrap import build_job_context
from wenyan.cli.status_scope import resolve_status_scope
from wenyan.jobs.context import JobContext, JobOptions
from wenyan_models.domain.ids import ChapterId, DocumentId, ParagraphId, SegmentId, document_id
from wenyan_models.domain.results import JobFailure, Promoted, Skipped, outcome_exit_code
from wenyan_models.domain.targets import SegmentTarget, paragraph_batch_target, single_segment_target

T = TypeVar("T")


def _repo_root():
    from pathlib import Path

    return Path.cwd()


def _bad_ref(exc: ValueError) -> NoReturn:
    raise typer.BadParameter(str(exc)) from exc


def _resolve_scope(
    ctx: JobContext,
    doc_id: DocumentId,
    *,
    chapter: str | None = None,
    paragraph: str | None = None,
    segment: str | None = None,
):
    try:
        return resolve_status_scope(
            ctx.artifacts,
            doc_id,
            "",
            chapter=chapter,
            paragraph=paragraph,
            segment=segment,
        )
    except ValueError as exc:
        _bad_ref(exc)


def resolve_document_context(document: str) -> tuple[JobContext, DocumentId]:
    ctx = build_job_context(_repo_root())
    entry = ctx.registry.resolve(document)
    doc_id = entry.document_id or document_id(document)
    return ctx, doc_id


def resolve_document_context_with_ref(document: str) -> tuple[JobContext, DocumentId, str]:
    ctx = build_job_context(_repo_root())
    entry = ctx.registry.resolve(document)
    if entry.document_id is None:
        raise typer.Exit(1)
    document_ref = entry.slug or document
    return ctx, entry.document_id, document_ref


def chapter_id_from_ref(
    ctx: JobContext,
    doc_id: DocumentId,
    chapter: str,
) -> ChapterId:
    scope = _resolve_scope(ctx, doc_id, chapter=chapter)
    if scope.chapter_id is None:
        raise typer.BadParameter("--chapter is required")
    return scope.chapter_id


def paragraph_id_from_ref(
    ctx: JobContext,
    doc_id: DocumentId,
    paragraph: str,
    *,
    chapter: str | None,
) -> ParagraphId:
    scope = _resolve_scope(ctx, doc_id, chapter=chapter, paragraph=paragraph)
    if scope.paragraph_id is None:
        raise typer.BadParameter("--paragraph is required")
    return scope.paragraph_id


def segment_id_from_ref(
    ctx: JobContext,
    doc_id: DocumentId,
    segment: str,
    *,
    chapter: str | None,
    paragraph: str | None,
) -> SegmentId:
    scope = _resolve_scope(
        ctx,
        doc_id,
        chapter=chapter,
        paragraph=paragraph,
        segment=segment,
    )
    if scope.segment_id is None:
        raise typer.BadParameter("--segment is required")
    return scope.segment_id


def segment_or_paragraph_batch_target(
    ctx: JobContext,
    doc_id: DocumentId,
    *,
    segment: str | None,
    paragraph: str | None,
    chapter: str | None,
) -> SegmentTarget:
    if segment is not None:
        return single_segment_target(
            segment_id_from_ref(ctx, doc_id, segment, chapter=chapter, paragraph=paragraph)
        )
    if paragraph is not None:
        return paragraph_batch_target(
            paragraph_id_from_ref(ctx, doc_id, paragraph, chapter=chapter)
        )
    raise typer.BadParameter("provide --segment or --paragraph")


def job_options(force: bool, dry_run: bool) -> JobOptions:
    return JobOptions(force=force, dry_run=dry_run)


def outcome_message(outcome: Promoted[T] | Skipped | JobFailure) -> str:
    match outcome:
        case Promoted():
            return "complete"
        case Skipped(reason=reason):
            return reason
        case JobFailure(message=message):
            return message


def emit_job_outcome(
    outcome: Promoted[T] | Skipped | JobFailure,
    *,
    as_json: bool,
) -> None:
    import json

    if as_json:
        typer.echo(json.dumps({"outcome": outcome.model_dump(by_alias=True)}))
    else:
        typer.echo(outcome_message(outcome))


def run_single_segment_job(
    document: str,
    segment: str,
    *,
    chapter: str | None,
    paragraph: str | None,
    runner: Callable[[JobContext, DocumentId, SegmentId, JobOptions], Promoted[T] | Skipped | JobFailure],
    force: bool,
    dry_run: bool,
    as_json: bool,
) -> None:
    ctx, doc_id = resolve_document_context(document)
    segment_id_value = segment_id_from_ref(
        ctx,
        doc_id,
        segment,
        chapter=chapter,
        paragraph=paragraph,
    )
    outcome = runner(ctx, doc_id, segment_id_value, job_options(force, dry_run))
    emit_job_outcome(outcome, as_json=as_json)
    raise typer.Exit(outcome_exit_code(outcome))
