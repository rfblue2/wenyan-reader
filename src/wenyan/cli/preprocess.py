import json
from pathlib import Path
from typing import Annotated, TypeVar

import typer

from wenyan.bootstrap import build_job_context
from wenyan.cli import preprocess_app
from wenyan.cli.options import dry_run_option, force_option, json_option
from wenyan.core.adapters.filesystem_graph_validator import FilesystemGraphValidator
from wenyan.core.adapters.filesystem_status_reader import FilesystemStatusReader
from wenyan.jobs.context import JobOptions
from wenyan.jobs.ingest_document import run_ingest_document
from wenyan.jobs.review_segment_tokenization import run_review_segment_tokenization
from wenyan.jobs.split_chapters import run_split_chapters
from wenyan.jobs.split_paragraphs import run_split_paragraphs
from wenyan.jobs.split_segments import run_split_segments
from wenyan.jobs.tokenize_segment import run_tokenize_segment
from wenyan_models.domain.ids import (
    chapter_id,
    document_id,
    paragraph_id,
    segment_id,
)
from wenyan_models.domain.results import JobFailure, Promoted, Skipped, outcome_exit_code
from wenyan_models.domain.targets import paragraph_batch_target, single_segment_target

T = TypeVar("T")


def _repo_root() -> Path:
    return Path.cwd()


def _job_options(force: bool, dry_run: bool) -> JobOptions:
    return JobOptions(force=force, dry_run=dry_run)


def _outcome_message(outcome: Promoted[T] | Skipped | JobFailure) -> str:
    match outcome:
        case Promoted():
            return "complete"
        case Skipped(reason=reason):
            return reason
        case JobFailure(message=message):
            return message


def _emit_json_or_text(outcome: Promoted[T] | Skipped | JobFailure, as_json: bool) -> None:
    if as_json:
        typer.echo(json.dumps({"outcome": outcome.model_dump(by_alias=True)}))
    else:
        typer.echo(_outcome_message(outcome))


@preprocess_app.command("ingest-document")
def ingest_document_cmd(
    source: Annotated[Path, typer.Argument(help="Source directory under sources/documents/<slug>/")],
    force: bool = force_option,
    dry_run: bool = dry_run_option,
    as_json: bool = json_option,
) -> None:
    ctx = build_job_context(_repo_root())
    outcome = run_ingest_document(ctx, source, _job_options(force, dry_run))
    _emit_json_or_text(outcome, as_json)
    raise typer.Exit(outcome_exit_code(outcome))


@preprocess_app.command("split-chapters")
def split_chapters_cmd(
    document: Annotated[str, typer.Argument(help="Document UUID or slug")],
    force: bool = force_option,
    dry_run: bool = dry_run_option,
    as_json: bool = json_option,
) -> None:
    ctx = build_job_context(_repo_root())
    entry = ctx.registry.resolve(document)
    doc_id = entry.document_id or document_id(document)
    outcome = run_split_chapters(ctx, doc_id, _job_options(force, dry_run))
    if as_json:
        typer.echo(json.dumps({"outcome": outcome.model_dump(by_alias=True)}))
    else:
        typer.echo(_outcome_message(outcome))
    raise typer.Exit(outcome_exit_code(outcome))


@preprocess_app.command("split-paragraphs")
def split_paragraphs_cmd(
    document: Annotated[str, typer.Argument()],
    chapter: Annotated[str, typer.Option("--chapter")],
    force: bool = force_option,
    dry_run: bool = dry_run_option,
    as_json: bool = json_option,
) -> None:
    ctx = build_job_context(_repo_root())
    entry = ctx.registry.resolve(document)
    doc_id = entry.document_id or document_id(document)
    outcome = run_split_paragraphs(
        ctx,
        doc_id,
        chapter_id(chapter),
        _job_options(force, dry_run),
    )
    if as_json:
        typer.echo(json.dumps({"outcome": outcome.model_dump(by_alias=True)}))
    else:
        typer.echo(_outcome_message(outcome))
    raise typer.Exit(outcome_exit_code(outcome))


@preprocess_app.command("split-segments")
def split_segments_cmd(
    document: Annotated[str, typer.Argument()],
    paragraph: Annotated[str, typer.Option("--paragraph")],
    force: bool = force_option,
    dry_run: bool = dry_run_option,
    as_json: bool = json_option,
) -> None:
    ctx = build_job_context(_repo_root())
    entry = ctx.registry.resolve(document)
    doc_id = entry.document_id or document_id(document)
    outcome = run_split_segments(
        ctx,
        doc_id,
        paragraph_id(paragraph),
        _job_options(force, dry_run),
    )
    if as_json:
        typer.echo(json.dumps({"outcome": outcome.model_dump(by_alias=True)}))
    else:
        typer.echo(_outcome_message(outcome))
    raise typer.Exit(outcome_exit_code(outcome))


@preprocess_app.command("tokenize-segment")
def tokenize_segment_cmd(
    document: Annotated[str, typer.Argument()],
    segment: Annotated[str | None, typer.Option("--segment")] = None,
    paragraph: Annotated[str | None, typer.Option("--paragraph")] = None,
    force: bool = force_option,
    dry_run: bool = dry_run_option,
    as_json: bool = json_option,
) -> None:
    if (segment is None) == (paragraph is None):
        raise typer.BadParameter("provide exactly one of --segment or --paragraph")
    ctx = build_job_context(_repo_root())
    entry = ctx.registry.resolve(document)
    doc_id = entry.document_id or document_id(document)
    target = (
        single_segment_target(segment_id(segment))
        if segment is not None
        else paragraph_batch_target(paragraph_id(paragraph or ""))
    )
    outcome = run_tokenize_segment(ctx, doc_id, target, _job_options(force, dry_run))
    if as_json:
        typer.echo(json.dumps({"outcome": outcome.model_dump(by_alias=True)}))
    else:
        typer.echo(_outcome_message(outcome))
    raise typer.Exit(outcome_exit_code(outcome))


@preprocess_app.command("review-segment-tokenization")
def review_segment_tokenization_cmd(
    document: Annotated[str, typer.Argument()],
    segment: Annotated[str, typer.Option("--segment")],
    force: bool = force_option,
    dry_run: bool = dry_run_option,
    as_json: bool = json_option,
) -> None:
    ctx = build_job_context(_repo_root())
    entry = ctx.registry.resolve(document)
    doc_id = entry.document_id or document_id(document)
    outcome = run_review_segment_tokenization(
        ctx,
        doc_id,
        segment_id(segment),
        _job_options(force, dry_run),
    )
    if as_json:
        typer.echo(json.dumps({"outcome": outcome.model_dump(by_alias=True)}))
    else:
        typer.echo(_outcome_message(outcome))
    raise typer.Exit(outcome_exit_code(outcome))


@preprocess_app.command("status")
def status_cmd(
    document: Annotated[str, typer.Argument()],
    as_json: bool = json_option,
) -> None:
    ctx = build_job_context(_repo_root())
    entry = ctx.registry.resolve(document)
    if entry.document_id is None:
        raise typer.Exit(1)
    reader = FilesystemStatusReader(ctx.artifacts, _repo_root())
    payload = reader.document_status(entry.document_id)
    if as_json:
        typer.echo(payload.model_dump_json(by_alias=True))
    else:
        typer.echo(payload.title)
    raise typer.Exit(0)


@preprocess_app.command("validate-artifacts")
def validate_artifacts_cmd(
    document: Annotated[str, typer.Argument()],
    as_json: bool = json_option,
) -> None:
    ctx = build_job_context(_repo_root())
    entry = ctx.registry.resolve(document)
    if entry.document_id is None:
        raise typer.Exit(1)
    validator = FilesystemGraphValidator(ctx.artifacts)
    report = validator.validate_document(entry.document_id)
    if as_json:
        typer.echo(report.model_dump_json(by_alias=True))
    else:
        typer.echo("ok" if report.ok else "invalid")
    raise typer.Exit(0 if report.ok else 1)


_STUBS = [
    "review-paragraph-structure",
    "gloss-segment",
    "review-segment-gloss",
    "annotate-segment-grammar",
    "review-segment-grammar",
    "annotate-segment-context",
    "review-segment-context",
    "assemble-paragraph",
    "package-document",
    "show",
    "review-report",
]


def _register_stub(name: str) -> None:
    def _stub(document: Annotated[str, typer.Argument()] = "") -> None:
        typer.echo(f"{name} is not implemented in this slice", err=True)
        raise typer.Exit(2)

    preprocess_app.command(name)(_stub)


for _command_name in _STUBS:
    _register_stub(_command_name)
