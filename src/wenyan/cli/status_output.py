from __future__ import annotations

from dataclasses import dataclass
from io import StringIO

from rich.console import Console
from rich.table import Table
from rich.text import Text

from wenyan_models.domain.enums import ReviewStatus, UnitStatus
from wenyan_models.show.segment import (
    ContextNoteShowItem,
    GrammarNoteShowItem,
    NoteCitationShowItem,
    SegmentShowView,
)
from wenyan_models.status.chapter import ChapterStatus
from wenyan_models.status.common import StatusCounts
from wenyan_models.status.document import DocumentStatus
from wenyan_models.status.paragraph import ParagraphStatus
from wenyan_models.status.payload import StatusPayload

_STATUS_STYLE: dict[UnitStatus, str] = {
    UnitStatus.COMPLETE: "green",
    UnitStatus.IN_PROGRESS: "yellow",
    UnitStatus.PENDING: "dim",
    UnitStatus.BLOCKED: "red bold",
    UnitStatus.FAILED: "red bold",
    UnitStatus.STALE: "magenta",
}

_REVIEW_STYLE: dict[ReviewStatus, str] = {
    ReviewStatus.APPROVED: "green",
    ReviewStatus.REJECTED: "red bold",
}


@dataclass(frozen=True)
class StatusDisplayContext:
    chapter_handle: str | None = None
    paragraph_handle: str | None = None
    segment_handle: str | None = None


StatusDisplayPayload = StatusPayload | SegmentShowView


def render_status(payload: StatusDisplayPayload, context: StatusDisplayContext) -> str:
    buffer = StringIO()
    console = Console(file=buffer, force_terminal=True, width=100, highlight=False)
    match payload:
        case DocumentStatus():
            _render_document(console, payload)
        case ChapterStatus():
            _render_chapter(console, payload, context)
        case ParagraphStatus():
            _render_paragraph(console, payload, context)
        case SegmentShowView():
            _render_segment(console, payload, context)
    return buffer.getvalue()


def _render_document(console: Console, payload: DocumentStatus) -> None:
    console.print(f"[bold]{payload.title}[/bold]")
    console.print(f"Document {payload.document_id}")
    console.print(
        f"Source {payload.source.status} · {payload.source.normalized_document_path or 'not ingested'}",
    )
    console.print(_counts_line(payload.counts, total_label="chapters", total=payload.counts.chapters))
    console.print()
    if not payload.chapters:
        console.print("[dim]No chapters yet.[/dim]")
        return
    console.print("[bold]Chapters[/bold]")
    for ordinal, chapter in enumerate(payload.chapters, start=1):
        progress = _unit_progress(
            chapter.progress.paragraphs_complete if chapter.progress else 0,
            chapter.progress.paragraphs_total if chapter.progress else None,
            "paragraphs",
        )
        line = Text()
        line.append(f"#{ordinal}  ", style="bold")
        line.append(chapter.status.value, style=_STATUS_STYLE[chapter.status])
        line.append(f"  {chapter.title}")
        if progress:
            line.append(f"  {progress}", style="dim")
        console.print(line)


def _render_chapter(console: Console, payload: ChapterStatus, context: StatusDisplayContext) -> None:
    chapter_handle = context.chapter_handle or str(payload.chapter_id)
    console.print(f"[bold]Chapter #{chapter_handle}[/bold]  {payload.chapter_id}")
    console.print(_counts_line(payload.counts, total_label="paragraphs", total=payload.counts.paragraphs))
    console.print()
    if not payload.paragraphs:
        console.print("[dim]No paragraphs yet.[/dim]")
        return
    console.print("[bold]Paragraphs[/bold]")
    for paragraph in payload.paragraphs:
        progress = _unit_progress(
            paragraph.progress.segments_complete if paragraph.progress else 0,
            paragraph.progress.segments_total if paragraph.progress else None,
            "segments",
        )
        line = Text()
        line.append(f"#{paragraph.ordinal}  ", style="bold")
        line.append(paragraph.status.value, style=_STATUS_STYLE[paragraph.status])
        if progress:
            line.append(f"  {progress}", style="dim")
        console.print(line)


def _render_paragraph(console: Console, payload: ParagraphStatus, context: StatusDisplayContext) -> None:
    chapter_handle = context.chapter_handle or str(payload.chapter_id)
    paragraph_handle = context.paragraph_handle or str(payload.paragraph_id)
    console.print(f"[bold]Paragraph #{paragraph_handle}[/bold]  {payload.paragraph_id}")
    console.print(f"Chapter #{chapter_handle}  {payload.chapter_id}")
    structure = payload.structure
    segment_count = structure.segment_count
    structure_detail = f"{segment_count} segments" if segment_count is not None else "not split"
    structure_line = Text("Structure ")
    structure_line.append(structure.status.value, style=_STATUS_STYLE[structure.status])
    structure_line.append(f" · {structure_detail}")
    console.print(structure_line)
    console.print(_counts_line(payload.counts, total_label="segments", total=payload.counts.segments))
    if payload.assembly is not None:
        console.print()
        console.print("[bold]Assembly[/bold]")
        component = payload.assembly
        line = Text()
        line.append(component.status.value, style=_STATUS_STYLE[component.status])
        line.append(f"  {component.kind.value}")
        if component.blocked_reason:
            line.append(f"  {component.blocked_reason}", style="red")
        console.print(line)
    console.print()
    if not payload.segments:
        console.print("[dim]No segments yet.[/dim]")
        return
    console.print("[bold]Segments[/bold]")
    for segment in payload.segments:
        progress = _unit_progress(
            segment.progress.components_complete if segment.progress else 0,
            segment.progress.components_total if segment.progress else None,
            "components",
        )
        line = Text()
        line.append(f"#{segment.ordinal}  ", style="bold")
        line.append(segment.status.value, style=_STATUS_STYLE[segment.status])
        line.append(f"  {segment.text_preview}")
        if progress:
            line.append(f"  {progress}", style="dim")
        if segment.blocked_component is not None:
            line.append(f"  blocked at {segment.blocked_component.value}", style="red")
        console.print(line)


def _render_segment(console: Console, payload: SegmentShowView, context: StatusDisplayContext) -> None:
    chapter_handle = context.chapter_handle or payload.chapter_handle
    paragraph_handle = context.paragraph_handle or payload.paragraph_handle
    segment_handle = context.segment_handle or payload.segment_handle
    location_parts: list[str] = []
    if chapter_handle is not None:
        location_parts.append(f"Chapter #{chapter_handle}")
    if paragraph_handle is not None:
        location_parts.append(f"Paragraph #{paragraph_handle}")
    if segment_handle is not None:
        location_parts.append(f"Segment #{segment_handle}")
    location = " · ".join(location_parts) if location_parts else "Segment"
    console.print(f"[bold]{payload.document_ref}[/bold]  {location}")
    console.print(
        f"[dim]{payload.chapter_id} · {payload.paragraph_id} · {payload.segment_id}[/dim]",
    )
    overall = Text("Overall ")
    overall.append(payload.status.value, style=_STATUS_STYLE[payload.status])
    console.print(overall)
    console.print()
    console.print(Text(payload.text))
    console.print()
    if payload.tokens:
        _render_gloss_table(console, payload)
    if payload.grammar_notes or payload.context_notes:
        console.print()
        _render_notes(console, payload)
    if payload.reviews:
        console.print()
        _render_reviews(console, payload)
    console.print()
    _render_components(console, payload)


def _render_gloss_table(console: Console, payload: SegmentShowView) -> None:
    has_glosses = any(row.gloss is not None for row in payload.tokens)
    title = "Glosses" if has_glosses else "Tokenization"
    table = Table(title=title, show_header=has_glosses, header_style="bold")
    table.add_column("Token")
    if has_glosses:
        table.add_column("Pinyin")
        table.add_column("Gloss")
        table.add_column("Decision")
    for row in payload.tokens:
        if has_glosses:
            table.add_row(
                row.surface,
                row.pinyin or "—",
                row.gloss or "—",
                row.decision or "—",
            )
        else:
            table.add_row(row.surface)
    console.print(table)


def _render_notes(console: Console, payload: SegmentShowView) -> None:
    if payload.grammar_notes:
        console.print("[bold]Grammar notes[/bold]")
        for note in payload.grammar_notes:
            _render_grammar_note(console, note)
    if payload.context_notes:
        console.print("[bold]Context notes[/bold]")
        for context_note in payload.context_notes:
            _render_context_note(console, context_note)


def _render_grammar_note(console: Console, note: GrammarNoteShowItem) -> None:
    anchors = ", ".join(note.anchor_surfaces) if note.anchor_surfaces else "—"
    console.print(f"  [{anchors}]  {note.body}")


def _render_context_note(console: Console, note: ContextNoteShowItem) -> None:
    anchors = ", ".join(note.anchor_surfaces) if note.anchor_surfaces else "—"
    console.print(f"  [{anchors}]  {note.body}")
    for source in note.sources:
        _render_citation(console, source)


def _render_citation(console: Console, source: NoteCitationShowItem) -> None:
    parts = [source.label]
    if source.url:
        parts.append(source.url)
    if source.excerpt:
        parts.append(source.excerpt)
    console.print(f"    [dim]Source: {' — '.join(parts)}[/dim]")


def _render_reviews(console: Console, payload: SegmentShowView) -> None:
    console.print("[bold]Reviews[/bold]")
    for review in payload.reviews:
        line = Text()
        line.append(review.kind.value, style="bold")
        line.append("  ")
        line.append(review.status.value, style=_REVIEW_STYLE[review.status])
        console.print(line)
        style = "red" if review.status == ReviewStatus.REJECTED else None
        for finding_line in review.finding_lines:
            console.print(f"  • {finding_line}", style=style)
        for item in review.source_grounding:
            note_id = item.get("noteId")
            supported = item.get("supported")
            source_indexes = item.get("sourceIndexes")
            if note_id is not None:
                console.print(
                    "    [dim]Grounding note "
                    f"{note_id}: supported={supported}, sourceIndexes={source_indexes}[/dim]",
                )


def _render_components(console: Console, payload: SegmentShowView) -> None:
    console.print("[bold]Components[/bold]")
    for component in payload.components:
        line = Text()
        line.append(component.status.value, style=_STATUS_STYLE[component.status])
        line.append(f"  {component.kind.value}")
        if component.blocked_reason:
            line.append(f"  {component.blocked_reason}", style="red")
        console.print(line)


def _counts_line(counts: StatusCounts, *, total_label: str, total: int | None) -> str:
    parts: list[str] = []
    if total is not None:
        parts.append(f"{total} {total_label}")
    if counts.complete:
        parts.append(f"{counts.complete} complete")
    if counts.in_progress:
        parts.append(f"{counts.in_progress} in-progress")
    if counts.pending:
        parts.append(f"{counts.pending} pending")
    if counts.blocked:
        parts.append(f"{counts.blocked} blocked")
    if counts.failed:
        parts.append(f"{counts.failed} failed")
    if not parts:
        return "No child units yet"
    return " · ".join(parts)


def _unit_progress(complete: int, total: int | None, unit: str) -> str:
    if total is None:
        return ""
    return f"({complete}/{total} {unit})"
