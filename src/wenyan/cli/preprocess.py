import json
from pathlib import Path
from typing import Annotated, TypeVar

import typer

from wenyan.cli import preprocess_app
from wenyan.cli.options import dry_run_option, force_option, json_option
from wenyan.cli.scope_options import (
    ChapterOption,
    OptionalSegmentOption,
    ParagraphOption,
    RequiredChapterOption,
    RequiredParagraphOption,
    SegmentOption,
)
from wenyan.cli.status_output import StatusDisplayContext, StatusDisplayPayload, render_status
from wenyan.cli.status_scope import build_display_context, resolve_status_scope
from wenyan.cli.unit_refs import (
    chapter_id_from_ref,
    emit_job_outcome,
    job_options,
    paragraph_id_from_ref,
    resolve_document_context,
    resolve_document_context_with_ref,
    run_single_segment_job,
    segment_id_from_ref,
    segment_or_paragraph_batch_target,
)
from wenyan.core.adapters.filesystem_graph_validator import FilesystemGraphValidator
from wenyan.core.adapters.filesystem_status_reader import FilesystemStatusReader
from wenyan.core.show.segment_view import build_segment_show_view
from wenyan.jobs.annotate_segment_context import run_annotate_segment_context
from wenyan.jobs.annotate_segment_grammar import run_annotate_segment_grammar
from wenyan.jobs.context import JobOptions
from wenyan.jobs.ingest_document import run_ingest_document
from wenyan.jobs.prune_orphan_segments import run_prune_orphan_segments
from wenyan.jobs.run_preprocess import run_preprocess
from wenyan.jobs.gloss_segment import run_gloss_segment
from wenyan.jobs.review_segment_context import run_review_segment_context
from wenyan.jobs.review_segment_gloss import run_review_segment_gloss
from wenyan.jobs.review_segment_grammar import run_review_segment_grammar
from wenyan.jobs.review_segment_tokenization import run_review_segment_tokenization
from wenyan.jobs.split_paragraphs import run_split_paragraphs
from wenyan.jobs.split_segments import run_split_segments
from wenyan.jobs.tokenize_segment import run_tokenize_segment
from wenyan_models.domain.results import JobFailure, Promoted, Skipped, outcome_exit_code

T = TypeVar("T")


def _repo_root() -> Path:
    return Path.cwd()


@preprocess_app.command("ingest-document")
def ingest_document_cmd(
    source: Annotated[Path, typer.Argument(help="Source directory under sources/documents/<slug>/")],
    force: bool = force_option,
    dry_run: bool = dry_run_option,
    as_json: bool = json_option,
) -> None:
    """Ingest a source directory, normalize text, and write normalized-document.json."""
    from wenyan.bootstrap import build_job_context

    ctx = build_job_context(_repo_root())
    outcome = run_ingest_document(ctx, source, job_options(force, dry_run))
    emit_job_outcome(outcome, as_json=as_json)
    raise typer.Exit(outcome_exit_code(outcome))


@preprocess_app.command("split-paragraphs")
def split_paragraphs_cmd(
    document: Annotated[str, typer.Argument(help="Document UUID or slug")],
    chapter: RequiredChapterOption,
    force: bool = force_option,
    dry_run: bool = dry_run_option,
    as_json: bool = json_option,
) -> None:
    """Propose paragraph spans for one chapter and validate coverage."""
    ctx, doc_id = resolve_document_context(document)
    outcome = run_split_paragraphs(
        ctx,
        doc_id,
        chapter_id_from_ref(ctx, doc_id, chapter),
        job_options(force, dry_run),
    )
    emit_job_outcome(outcome, as_json=as_json)
    raise typer.Exit(outcome_exit_code(outcome))


@preprocess_app.command("split-segments")
def split_segments_cmd(
    document: Annotated[str, typer.Argument(help="Document UUID or slug")],
    paragraph: RequiredParagraphOption,
    chapter: ChapterOption = None,
    force: bool = force_option,
    dry_run: bool = dry_run_option,
    as_json: bool = json_option,
) -> None:
    """Propose segment boundaries for one paragraph and create segment job inputs."""
    ctx, doc_id = resolve_document_context(document)
    outcome = run_split_segments(
        ctx,
        doc_id,
        paragraph_id_from_ref(ctx, doc_id, paragraph, chapter=chapter),
        job_options(force, dry_run),
    )
    emit_job_outcome(outcome, as_json=as_json)
    raise typer.Exit(outcome_exit_code(outcome))


def _run_segment_or_paragraph_batch_cmd(
    document: str,
    *,
    segment: str | None,
    paragraph: str | None,
    chapter: str | None,
    runner,
    force: bool,
    dry_run: bool,
    as_json: bool,
) -> None:
    ctx, doc_id = resolve_document_context(document)
    target = segment_or_paragraph_batch_target(
        ctx,
        doc_id,
        segment=segment,
        paragraph=paragraph,
        chapter=chapter,
    )
    outcome = runner(ctx, doc_id, target, job_options(force, dry_run))
    emit_job_outcome(outcome, as_json=as_json)
    raise typer.Exit(outcome_exit_code(outcome))


@preprocess_app.command("tokenize-segment")
def tokenize_segment_cmd(
    document: Annotated[str, typer.Argument(help="Document UUID or slug")],
    segment: OptionalSegmentOption = None,
    paragraph: ParagraphOption = None,
    chapter: ChapterOption = None,
    force: bool = force_option,
    dry_run: bool = dry_run_option,
    as_json: bool = json_option,
) -> None:
    """Identify glossable token occurrences for one segment or a paragraph batch."""
    _run_segment_or_paragraph_batch_cmd(
        document,
        segment=segment,
        paragraph=paragraph,
        chapter=chapter,
        runner=run_tokenize_segment,
        force=force,
        dry_run=dry_run,
        as_json=as_json,
    )


@preprocess_app.command("review-segment-tokenization")
def review_segment_tokenization_cmd(
    document: Annotated[str, typer.Argument(help="Document UUID or slug")],
    segment: SegmentOption,
    chapter: ChapterOption = None,
    paragraph: ParagraphOption = None,
    force: bool = force_option,
    dry_run: bool = dry_run_option,
    as_json: bool = json_option,
) -> None:
    """Review token boundaries and offsets for one segment tokenization."""
    run_single_segment_job(
        document,
        segment,
        chapter=chapter,
        paragraph=paragraph,
        runner=run_review_segment_tokenization,
        force=force,
        dry_run=dry_run,
        as_json=as_json,
    )


@preprocess_app.command("gloss-segment")
def gloss_segment_cmd(
    document: Annotated[str, typer.Argument(help="Document UUID or slug")],
    segment: OptionalSegmentOption = None,
    paragraph: ParagraphOption = None,
    chapter: ChapterOption = None,
    force: bool = force_option,
    dry_run: bool = dry_run_option,
    as_json: bool = json_option,
) -> None:
    """Select or propose glosses for reviewed token occurrences."""
    _run_segment_or_paragraph_batch_cmd(
        document,
        segment=segment,
        paragraph=paragraph,
        chapter=chapter,
        runner=run_gloss_segment,
        force=force,
        dry_run=dry_run,
        as_json=as_json,
    )


@preprocess_app.command("review-segment-gloss")
def review_segment_gloss_cmd(
    document: Annotated[str, typer.Argument(help="Document UUID or slug")],
    segment: SegmentOption,
    chapter: ChapterOption = None,
    paragraph: ParagraphOption = None,
    force: bool = force_option,
    dry_run: bool = dry_run_option,
    as_json: bool = json_option,
) -> None:
    """Review gloss sense selection and homonym handling for one segment."""
    run_single_segment_job(
        document,
        segment,
        chapter=chapter,
        paragraph=paragraph,
        runner=run_review_segment_gloss,
        force=force,
        dry_run=dry_run,
        as_json=as_json,
    )


@preprocess_app.command("annotate-segment-grammar")
def annotate_segment_grammar_cmd(
    document: Annotated[str, typer.Argument(help="Document UUID or slug")],
    segment: OptionalSegmentOption = None,
    paragraph: ParagraphOption = None,
    chapter: ChapterOption = None,
    force: bool = force_option,
    dry_run: bool = dry_run_option,
    as_json: bool = json_option,
) -> None:
    """Draft grammar notes anchored to segment tokens."""
    _run_segment_or_paragraph_batch_cmd(
        document,
        segment=segment,
        paragraph=paragraph,
        chapter=chapter,
        runner=run_annotate_segment_grammar,
        force=force,
        dry_run=dry_run,
        as_json=as_json,
    )


@preprocess_app.command("review-segment-grammar")
def review_segment_grammar_cmd(
    document: Annotated[str, typer.Argument(help="Document UUID or slug")],
    segment: SegmentOption,
    chapter: ChapterOption = None,
    paragraph: ParagraphOption = None,
    force: bool = force_option,
    dry_run: bool = dry_run_option,
    as_json: bool = json_option,
) -> None:
    """Review grammar notes for accuracy and usefulness."""
    run_single_segment_job(
        document,
        segment,
        chapter=chapter,
        paragraph=paragraph,
        runner=run_review_segment_grammar,
        force=force,
        dry_run=dry_run,
        as_json=as_json,
    )


@preprocess_app.command("annotate-segment-context")
def annotate_segment_context_cmd(
    document: Annotated[str, typer.Argument(help="Document UUID or slug")],
    segment: OptionalSegmentOption = None,
    paragraph: ParagraphOption = None,
    chapter: ChapterOption = None,
    force: bool = force_option,
    dry_run: bool = dry_run_option,
    as_json: bool = json_option,
) -> None:
    """Draft segment-local context notes with source grounding."""
    _run_segment_or_paragraph_batch_cmd(
        document,
        segment=segment,
        paragraph=paragraph,
        chapter=chapter,
        runner=run_annotate_segment_context,
        force=force,
        dry_run=dry_run,
        as_json=as_json,
    )


@preprocess_app.command("review-segment-context")
def review_segment_context_cmd(
    document: Annotated[str, typer.Argument(help="Document UUID or slug")],
    segment: SegmentOption,
    chapter: ChapterOption = None,
    paragraph: ParagraphOption = None,
    force: bool = force_option,
    dry_run: bool = dry_run_option,
    as_json: bool = json_option,
) -> None:
    """Review context notes for usefulness and grounding."""
    run_single_segment_job(
        document,
        segment,
        chapter=chapter,
        paragraph=paragraph,
        runner=run_review_segment_context,
        force=force,
        dry_run=dry_run,
        as_json=as_json,
    )


@preprocess_app.command("run")
def run_cmd(
    document: Annotated[str, typer.Argument(help="Document UUID or slug")],
    segment: OptionalSegmentOption = None,
    chapter: ChapterOption = None,
    paragraph: ParagraphOption = None,
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
    ctx, doc_id = resolve_document_context(document)
    use_next_segment = next_segment or (not next_paragraph and segment is None)
    segment_id_value = (
        segment_id_from_ref(ctx, doc_id, segment, chapter=chapter, paragraph=paragraph)
        if segment
        else None
    )
    outcome = run_preprocess(
        ctx,
        doc_id,
        segment_id_value=segment_id_value,
        next_segment=use_next_segment,
        next_paragraph=next_paragraph,
        options=job_options(force, dry_run),
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
    chapter: ChapterOption = None,
    paragraph: ParagraphOption = None,
    segment: OptionalSegmentOption = None,
    as_json: bool = json_option,
) -> None:
    """Report preprocessing progress; segment scope includes source text and artifacts."""
    ctx, doc_id, document_ref = resolve_document_context_with_ref(document)
    reader = FilesystemStatusReader(ctx.artifacts, _repo_root())
    payload: StatusDisplayPayload
    try:
        scope = resolve_status_scope(
            ctx.artifacts,
            doc_id,
            document_ref,
            chapter=chapter,
            paragraph=paragraph,
            segment=segment,
        )
        chapter_handle, paragraph_handle, segment_handle = build_display_context(
            ctx.artifacts,
            doc_id,
            scope,
        )
        match scope.level:
            case "segment":
                assert scope.segment_id is not None
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
            case "paragraph":
                assert scope.paragraph_id is not None
                payload = reader.paragraph_status(doc_id, scope.paragraph_id)
            case "chapter":
                assert scope.chapter_id is not None
                payload = reader.chapter_status(doc_id, scope.chapter_id)
            case "document":
                payload = reader.document_status(doc_id)
        display = StatusDisplayContext(
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
        typer.echo(render_status(payload, display), nl=False)
    raise typer.Exit(0)


@preprocess_app.command("prune")
def prune_cmd(
    document: Annotated[str, typer.Argument(help="Document UUID or slug")],
    dry_run: bool = dry_run_option,
    as_json: bool = json_option,
) -> None:
    """Remove segment job directories not referenced by any current paragraph draft."""
    ctx, doc_id = resolve_document_context_with_ref(document)
    outcome = run_prune_orphan_segments(ctx, doc_id, JobOptions(dry_run=dry_run))
    if as_json:
        typer.echo(json.dumps({"outcome": outcome.model_dump(by_alias=True)}))
    else:
        match outcome:
            case Skipped(reason=reason):
                typer.echo(reason)
            case Promoted(artifact=result):
                action = "would remove" if result.dry_run else "removed"
                typer.echo(f"{action} {len(result.removed)} orphaned segment(s)")
                for item in result.removed:
                    preview = f" — {item.text_preview}" if item.text_preview else ""
                    typer.echo(f"  {item.segment_id}{preview}")
            case JobFailure(message=message):
                typer.echo(message, err=True)
    raise typer.Exit(outcome_exit_code(outcome))


@preprocess_app.command("validate-artifacts")
def validate_artifacts_cmd(
    document: Annotated[str, typer.Argument(help="Document UUID or slug")],
    chapter: ChapterOption = None,
    paragraph: ParagraphOption = None,
    segment: OptionalSegmentOption = None,
    as_json: bool = json_option,
) -> None:
    """Check artifact graph integrity without generating new content."""
    ctx, doc_id, document_ref = resolve_document_context_with_ref(document)
    validator = FilesystemGraphValidator(ctx.artifacts, ctx.repo_root)
    try:
        scope = resolve_status_scope(
            ctx.artifacts,
            doc_id,
            document_ref,
            chapter=chapter,
            paragraph=paragraph,
            segment=segment,
        )
    except ValueError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc
    match scope.level:
        case "segment":
            assert scope.segment_id is not None
            report = validator.validate_segment(doc_id, scope.segment_id)
        case "paragraph":
            assert scope.paragraph_id is not None
            report = validator.validate_paragraph(doc_id, scope.paragraph_id)
        case "chapter":
            assert scope.chapter_id is not None
            report = validator.validate_chapter(doc_id, scope.chapter_id)
        case "document":
            report = validator.validate_document(doc_id)
    if as_json:
        typer.echo(report.model_dump_json(by_alias=True))
    else:
        typer.echo("ok" if report.ok else "invalid")
    raise typer.Exit(0 if report.ok else 1)


@preprocess_app.command("review-paragraph-structure")
def review_paragraph_structure_cmd(
    document: Annotated[str, typer.Argument(help="Document UUID or slug")],
    paragraph: RequiredParagraphOption,
    chapter: ChapterOption = None,
) -> None:
    """Review segment boundaries and paragraph structure quality."""
    typer.echo("review-paragraph-structure is not implemented in this slice", err=True)
    raise typer.Exit(2)


@preprocess_app.command("assemble-paragraph")
def assemble_paragraph_cmd(
    document: Annotated[str, typer.Argument(help="Document UUID or slug")],
    paragraph: RequiredParagraphOption,
    chapter: ChapterOption = None,
) -> None:
    """Assemble completed segment outputs into a reader paragraph file."""
    typer.echo("assemble-paragraph is not implemented in this slice", err=True)
    raise typer.Exit(2)


@preprocess_app.command("package-document")
def package_document_cmd(
    document: Annotated[str, typer.Argument(help="Document UUID or slug")],
) -> None:
    """Build validated reader package files under content/documents/."""
    typer.echo("package-document is not implemented in this slice", err=True)
    raise typer.Exit(2)


@preprocess_app.command("review-report")
def review_report_cmd(
    document: Annotated[str, typer.Argument(help="Document UUID or slug")],
    segment: SegmentOption,
    chapter: ChapterOption = None,
    paragraph: ParagraphOption = None,
) -> None:
    """Print the latest review report for a segment or component."""
    typer.echo("review-report is not implemented in this slice", err=True)
    raise typer.Exit(2)
