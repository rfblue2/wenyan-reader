from __future__ import annotations

from collections.abc import Sequence

from wenyan_models.artifacts.paragraph import ParagraphDraft
from wenyan_models.artifacts.segment import ContextNoteItem, NoteCitation, NoteItem
from wenyan_models.domain.ids import segment_id
from wenyan_models.reader.paragraph import (
    ParagraphPackage,
    ReaderNote,
    ReaderNoteSource,
    ReaderSegment,
    ReaderToken,
)

from wenyan.core.assembly.state import SegmentOutputs


def compile_paragraph_package(
    draft: ParagraphDraft,
    segments: Sequence[SegmentOutputs],
) -> ParagraphPackage:
    compiled = tuple(_compile_segment(segment) for segment in segments)
    return ParagraphPackage(
        id=draft.paragraph_id,
        segments=_fold_paragraph_context_notes(draft, compiled),
    )


def _compile_segment(output: SegmentOutputs) -> ReaderSegment:
    gloss_by_token = {decision.token_id: decision.gloss_id for decision in output.glosses.gloss_decisions}
    tokens = tuple(
        ReaderToken(
            id=token.id,
            surface=token.surface,
            start=token.start,
            end=token.end,
            glossId=gloss_by_token.get(token.id, ""),
        )
        for token in output.tokenization.tokens
    )
    notes: list[ReaderNote] = [
        *_grammar_notes_to_reader(output.grammar_notes.grammar_notes),
        *_context_notes_to_reader(output.context_notes.context_notes),
    ]
    return ReaderSegment(
        id=output.segment_id,
        text=output.tokenization.text,
        newGlossIds=output.glosses.new_gloss_ids,
        tokens=tokens,
        notes=tuple(notes),
    )


def _grammar_notes_to_reader(notes: tuple[NoteItem, ...]) -> tuple[ReaderNote, ...]:
    return tuple(
        ReaderNote(
            id=note.id,
            type="grammar",
            anchorTokenIds=note.anchor_token_ids,
            body=note.body,
        )
        for note in notes
    )


def _context_notes_to_reader(notes: tuple[ContextNoteItem, ...]) -> tuple[ReaderNote, ...]:
    return tuple(
        ReaderNote(
            id=note.id,
            type="context",
            anchorTokenIds=note.anchor_token_ids,
            body=note.body,
            sources=tuple(_citation_to_reader_source(source) for source in note.sources),
        )
        for note in notes
    )


def _citation_to_reader_source(citation: NoteCitation) -> ReaderNoteSource:
    return ReaderNoteSource(label=citation.label, detail=citation.excerpt)


def _source_to_reader(source: NoteCitation | str) -> ReaderNoteSource:
    if isinstance(source, NoteCitation):
        return _citation_to_reader_source(source)
    return ReaderNoteSource(label=str(source), detail="")


def _fold_paragraph_context_notes(
    draft: ParagraphDraft,
    segments: tuple[ReaderSegment, ...],
) -> tuple[ReaderSegment, ...]:
    updated = list(segments)
    index_by_id = {segment.id: index for index, segment in enumerate(segments)}
    for note in draft.paragraph_context_notes:
        if not note.anchor_segment_ids:
            raise ValueError(f"paragraph context note {note.id} has no anchor segment ids")
        target_segment_id = segment_id(note.anchor_segment_ids[0])
        index = index_by_id.get(target_segment_id)
        if index is None:
            raise ValueError(
                f"paragraph context note {note.id} anchors unknown segment {target_segment_id}",
            )
        segment = updated[index]
        anchor = min(segment.tokens, key=lambda token: token.start).id if segment.tokens else ""
        reader_note = ReaderNote(
            id=note.id,
            type="context",
            anchorTokenIds=(anchor,),
            body=note.body,
            sources=tuple(_source_to_reader(source) for source in note.sources),
        )
        updated[index] = segment.model_copy(update={"notes": segment.notes + (reader_note,)})
    return tuple(updated)
