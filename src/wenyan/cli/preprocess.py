import json
from pathlib import Path
from typing import Annotated, TypeVar

import typer

from wenyan.bootstrap import build_job_context
from wenyan.cli import preprocess_app
from wenyan.cli.options import dry_run_option, force_option, json_option
from wenyan.cli.show_output import ShowDisplayContext, render_segment_show
from wenyan.cli.status_output import StatusDisplayContext, render_status
from wenyan.cli.status_scope import build_display_context, resolve_status_scope, segment_handle_for_id
from wenyan.core.adapters.filesystem_graph_validator import FilesystemGraphValidator
from wenyan.core.adapters.filesystem_status_reader import FilesystemStatusReader
from wenyan.core.show.segment_view import build_segment_show_view
from wenyan.core.status.derivation import find_segment_location
from wenyan.jobs.context import JobOptions
from wenyan.jobs.ingest_document import run_ingest_document
from wenyan.jobs.run_preprocess import RunPlan, run_preprocess
from wenyan.jobs.gloss_segment import run_gloss_segment
from wenyan.jobs.review_segment_gloss import run_review_segment_gloss
from wenyan.jobs.review_segment_tokenization import run_review_segment_tokenization
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
from wenyan_models.status.payload import StatusPayload

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
    """Ingest a source directory, normalize text, and write normalized-document.json."""
    ctx = build_job_context(_repo_root())
    outcome = run_ingest_document(ctx, source, _job_options(force, dry_run))
    _emit_json_or_text(outcome, as_json)
    raise typer.Exit(outcome_exit_code(outcome))


@preprocess_app.command("split-paragraphs")
def split_paragraphs_cmd(
    document: Annotated[str, typer.Argument(help="Document UUID or slug")],
    chapter: Annotated[str, typer.Option("--chapter", help="Chapter UUID")],
    force: bool = force_option,
    dry_run: bool = dry_run_option,
    as_json: bool = json_option,
) -> None:
    """Propose paragraph spans for one chapter and validate coverage."""
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
    document: Annotated[str, typer.Argument(help="Document UUID or slug")],
    paragraph: Annotated[str, typer.Option("--paragraph", help="Paragraph UUID")],
    force: bool = force_option,
    dry_run: bool = dry_run_option,
    as_json: bool = json_option,
) -> None:
    """Propose segment boundaries for one paragraph and create segment job inputs."""
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
    document: Annotated[str, typer.Argument(help="Document UUID or slug")],
    segment: Annotated[str | None, typer.Option("--segment", help="Single segment UUID")] = None,
    paragraph: Annotated[
        str | None,
        typer.Option("--paragraph", help="Run all pending segments under this paragraph"),
    ] = None,
    force: bool = force_option,
    dry_run: bool = dry_run_option,
    as_json: bool = json_option,
) -> None:
    """Identify glossable token occurrences for one segment or a paragraph batch."""
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
    document: Annotated[str, typer.Argument(help="Document UUID or slug")],
    segment: Annotated[str, typer.Option("--segment", help="Segment UUID")],
    force: bool = force_option,
    dry_run: bool = dry_run_option,
    as_json: bool = json_option,
) -> None:
    """Review token boundaries and offsets for one segment tokenization."""
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


@preprocess_app.command("gloss-segment")
def gloss_segment_cmd(
    document: Annotated[str, typer.Argument(help="Document UUID or slug")],
    segment: Annotated[str | None, typer.Option("--segment", help="Single segment UUID")] = None,
    paragraph: Annotated[
        str | None,
        typer.Option("--paragraph", help="Run all pending segments under this paragraph"),
    ] = None,
    force: bool = force_option,
    dry_run: bool = dry_run_option,
    as_json: bool = json_option,
) -> None:
    """Select or propose glosses for reviewed token occurrences."""
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
    outcome = run_gloss_segment(ctx, doc_id, target, _job_options(force, dry_run))
    if as_json:
        typer.echo(json.dumps({"outcome": outcome.model_dump(by_alias=True)}))
    else:
        typer.echo(_outcome_message(outcome))
    raise typer.Exit(outcome_exit_code(outcome))


@preprocess_app.command("review-segment-gloss")
def review_segment_gloss_cmd(
    document: Annotated[str, typer.Argument(help="Document UUID or slug")],
    segment: Annotated[str, typer.Option("--segment", help="Segment UUID")],
    force: bool = force_option,
    dry_run: bool = dry_run_option,
    as_json: bool = json_option,
) -> None:
    """Review gloss sense selection and homonym handling for one segment."""
    ctx = build_job_context(_repo_root())
    entry = ctx.registry.resolve(document)
    doc_id = entry.document_id or document_id(document)
    outcome = run_review_segment_gloss(
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


@preprocess_app.command("run")
def run_cmd(
    document: Annotated[str, typer.Argument(help="Document UUID or slug")],
    segment: Annotated[str | None, typer.Option("--segment", help="Segment UUID")] = None,
    next_segment: Annotated[
        bool,
        typer.Option(
            "--next-segment",
            help="Process the next incomplete segment through all subjobs (default)",
        ),
    ] = False,
    next_paragraph: Annotated[
        bool,
        typer.Option(
            "--next-paragraph",
            help="Prepare segment structure for the next paragraph lacking a draft",
        ),
    ] = False,
    force: bool = force_option,
    dry_run: bool = dry_run_option,
    as_json: bool = json_option,
) -> None:
    """Run preprocessing for the next segment, a named segment, or the next paragraph."""
    ctx = build_job_context(_repo_root())
    entry = ctx.registry.resolve(document)
    doc_id = entry.document_id or document_id(document)
    use_next_segment = next_segment or (not next_paragraph and segment is None)
    outcome = run_preprocess(
        ctx,
        doc_id,
        segment_id_value=segment_id(segment) if segment else None,
        next_segment=use_next_segment,
        next_paragraph=next_paragraph,
        options=_job_options(force, dry_run),
    )
    if as_json:
        typer.echo(json.dumps({"outcome": outcome.model_dump(by_alias=True)}))
    else:
        match outcome:
            case Promoted(artifact=plan):
                stages = ", ".join(plan.stages_run) if plan.stages_run else "none"
                target = plan.segment_id or plan.paragraph_id or doc_id
                preview = f" ({plan.text_preview})" if plan.text_preview else ""
                typer.echo(f"complete ({stages}) for {target}{preview}")
            case Skipped(reason=reason):
                typer.echo(reason)
            case JobFailure(message=message):
                typer.echo(message, err=True)
    raise typer.Exit(outcome_exit_code(outcome))


@preprocess_app.command("status")
def status_cmd(
    document: Annotated[str, typer.Argument(help="Document UUID or slug")],
    chapter: Annotated[
        str | None,
        typer.Option(
            "--chapter",
            help="Chapter UUID, number (e.g. 1), or title (e.g. 始計第一)",
        ),
    ] = None,
    paragraph: Annotated[
        str | None,
        typer.Option(
            "--paragraph",
            help="Paragraph UUID or number (requires --chapter for numbers)",
        ),
    ] = None,
    segment: Annotated[
        str | None,
        typer.Option(
            "--segment",
            help="Segment UUID or number (requires --paragraph for numbers)",
        ),
    ] = None,
    as_json: bool = json_option,
) -> None:
    """Report preprocessing progress for a document and its child units."""
    ctx = build_job_context(_repo_root())
    entry = ctx.registry.resolve(document)
    if entry.document_id is None:
        raise typer.Exit(1)
    reader = FilesystemStatusReader(ctx.artifacts, _repo_root())
    doc_id = entry.document_id
    document_ref = entry.slug or document
    payload: StatusPayload
    try:
        scope = resolve_status_scope(
            ctx.artifacts,
            doc_id,
            document_ref,
            chapter=chapter,
            paragraph=paragraph,
            segment=segment,
        )
        match scope.level:
            case "segment":
                assert scope.segment_id is not None
                payload = reader.segment_status(doc_id, scope.segment_id)
            case "paragraph":
                assert scope.paragraph_id is not None
                payload = reader.paragraph_status(doc_id, scope.paragraph_id)
            case "chapter":
                assert scope.chapter_id is not None
                payload = reader.chapter_status(doc_id, scope.chapter_id)
            case "document":
                payload = reader.document_status(doc_id)
        chapter_handle, paragraph_handle = build_display_context(ctx.artifacts, doc_id, scope)
        display = StatusDisplayContext(
            chapter_handle=chapter_handle,
            paragraph_handle=paragraph_handle,
        )
    except ValueError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc
    if as_json:
        typer.echo(payload.model_dump_json(by_alias=True))
    else:
        typer.echo(render_status(payload, display), nl=False)
    raise typer.Exit(0)


@preprocess_app.command("show")
def show_cmd(
    document: Annotated[str, typer.Argument(help="Document UUID or slug")],
    segment: Annotated[
        str,
        typer.Option("--segment", help="Segment UUID or number (requires --paragraph for numbers)"),
    ],
    chapter: Annotated[
        str | None,
        typer.Option(
            "--chapter",
            help="Chapter UUID, number (e.g. 1), or title (e.g. 始計第一)",
        ),
    ] = None,
    paragraph: Annotated[
        str | None,
        typer.Option(
            "--paragraph",
            help="Paragraph UUID or number (requires --chapter for numbers)",
        ),
    ] = None,
    as_json: bool = json_option,
) -> None:
    """Show a segment's source text and generated artifacts in an editor-friendly format."""
    ctx = build_job_context(_repo_root())
    entry = ctx.registry.resolve(document)
    if entry.document_id is None:
        raise typer.Exit(1)
    doc_id = entry.document_id
    document_ref = entry.slug or document
    try:
        scope = resolve_status_scope(
            ctx.artifacts,
            doc_id,
            document_ref,
            chapter=chapter,
            paragraph=paragraph,
            segment=segment,
        )
        if scope.segment_id is None:
            raise ValueError("--segment is required")
        chapter_handle, paragraph_handle = build_display_context(ctx.artifacts, doc_id, scope)
        segment_handle = scope.segment_handle
        if segment_handle is None:
            paragraph_id_value = scope.paragraph_id
            if paragraph_id_value is None:
                location = find_segment_location(ctx.artifacts, doc_id, scope.segment_id)
                if location is not None:
                    _, paragraph_id_value, _ = location
            if paragraph_id_value is not None:
                segment_handle = segment_handle_for_id(
                    ctx.artifacts,
                    doc_id,
                    paragraph_id_value,
                    scope.segment_id,
                )
        payload = build_segment_show_view(
            ctx.artifacts,
            _repo_root(),
            document_id=doc_id,
            document_ref=document_ref,
            segment_id=scope.segment_id,
            chapter_handle=chapter_handle,
            paragraph_handle=paragraph_handle,
            segment_handle=segment_handle,
        )
        display = ShowDisplayContext(
            chapter_handle=chapter_handle,
            paragraph_handle=paragraph_handle,
            segment_handle=segment_handle,
        )
    except ValueError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc
    if as_json:
        typer.echo(payload.model_dump_json(by_alias=True))
    else:
        typer.echo(render_segment_show(payload, display), nl=False)
    raise typer.Exit(0)


@preprocess_app.command("validate-artifacts")
def validate_artifacts_cmd(
    document: Annotated[str, typer.Argument(help="Document UUID or slug")],
    as_json: bool = json_option,
) -> None:
    """Check artifact graph integrity without generating new content."""
    ctx = build_job_context(_repo_root())
    entry = ctx.registry.resolve(document)
    if entry.document_id is None:
        raise typer.Exit(1)
    validator = FilesystemGraphValidator(ctx.artifacts, ctx.repo_root)
    report = validator.validate_document(entry.document_id)
    if as_json:
        typer.echo(report.model_dump_json(by_alias=True))
    else:
        typer.echo("ok" if report.ok else "invalid")
    raise typer.Exit(0 if report.ok else 1)


_STUB_HELP: dict[str, str] = {
    "review-paragraph-structure": "Review segment boundaries and paragraph structure quality.",
    "annotate-segment-grammar": "Draft grammar notes anchored to segment tokens.",
    "review-segment-grammar": "Review grammar notes for accuracy and usefulness.",
    "annotate-segment-context": "Draft segment-local context notes with source grounding.",
    "review-segment-context": "Review context notes for usefulness and grounding.",
    "assemble-paragraph": "Assemble completed segment outputs into a reader paragraph file.",
    "package-document": "Build validated reader package files under content/documents/.",
    "review-report": "Print the latest review report for a segment or component.",
}


def _register_stub(name: str, help_text: str) -> None:
    def _stub(document: Annotated[str, typer.Argument(help="Document UUID or slug")] = "") -> None:
        typer.echo(f"{name} is not implemented in this slice", err=True)
        raise typer.Exit(2)

    _stub.__doc__ = help_text
    preprocess_app.command(name)(_stub)


for _command_name, _help_text in _STUB_HELP.items():
    _register_stub(_command_name, _help_text)
