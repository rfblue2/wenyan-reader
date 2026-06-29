from __future__ import annotations

from dataclasses import dataclass
from io import StringIO

from rich.console import Console
from rich.table import Table
from rich.text import Text

from wenyan_models.domain.enums import ReviewStatus, UnitStatus
from wenyan_models.show.segment import NoteShowItem, SegmentShowView

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
class ShowDisplayContext:
    chapter_handle: str | None = None
    paragraph_handle: str | None = None
    segment_handle: str | None = None


def render_segment_show(payload: SegmentShowView, context: ShowDisplayContext) -> str:
    buffer = StringIO()
    console = Console(file=buffer, force_terminal=True, width=100, highlight=False)
    _render_header(console, payload, context)
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
    return buffer.getvalue()


def _render_header(console: Console, payload: SegmentShowView, context: ShowDisplayContext) -> None:
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
            _render_note(console, note)
    if payload.context_notes:
        console.print("[bold]Context notes[/bold]")
        for note in payload.context_notes:
            _render_note(console, note)


def _render_note(console: Console, note: NoteShowItem) -> None:
    anchors = ", ".join(note.anchor_surfaces) if note.anchor_surfaces else "—"
    console.print(f"  [{anchors}]  {note.body}")
    for source in note.sources:
        detail = f" — {source.detail}" if source.detail else ""
        console.print(f"    [dim]Source: {source.label}{detail}[/dim]")


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
            source_ids = item.get("sourceIds")
            if note_id is not None:
                console.print(
                    f"    [dim]Grounding note {note_id}: supported={supported}, sources={source_ids}[/dim]",
                )


def _render_components(console: Console, payload: SegmentShowView) -> None:
    console.print("[bold]Components[/bold]")
    for component in payload.components:
        line = Text()
        line.append(component.status.value, style=_STATUS_STYLE[component.status])
        line.append(f"  {component.kind.value}")
        console.print(line)
