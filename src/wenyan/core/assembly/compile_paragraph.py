from __future__ import annotations

from collections.abc import Sequence

from wenyan_models.artifacts.paragraph import ParagraphDraft
from wenyan_models.artifacts.segment import ContextNoteItem, GrammarNoteItem, NoteCitation
from wenyan_models.domain.ids import SegmentId, segment_id
from wenyan_models.reader.paragraph import (
    ParagraphPackage,
    ReaderNote,
    ReaderNoteSource,
    ReaderSegment,
    ReaderToken,
)

from wenyan.core.assembly.load_segment_outputs import CompiledSegmentInputs


def compile_paragraph_package(
    draft: ParagraphDraft,
    outputs: Sequence[CompiledSegmentInputs],
) -> ParagraphPackage:
    outputs_by_id = {output.segment_id: output for output in outputs}
    segments = tuple(
        _compile_segment(outputs_by_id[draft_segment.id])
        for draft_segment in draft.segments
    )
    segments = _fold_paragraph_context_notes(draft, segments, outputs_by_id)
    return ParagraphPackage(id=draft.paragraph_id, segments=segments)


def _compile_segment(output: CompiledSegmentInputs) -> ReaderSegment:
    gloss_by_token = {decision.token_id: decision.gloss_id for decision in output.glosses.gloss_decisions}
    tokens = tuple(
        ReaderToken(
            id=token.id,
            surface=token.surface,
            start=token.start,
            end=token.end,
            gloss_id=gloss_by_token.get(token.id, ""),
        )
        for token in output.tokenization.tokens
    )
    notes: list[ReaderNote] = [
        *_grammar_notes_to_reader(output.grammar_notes.grammar_notes),
        *_context_notes_to_reader(output.context_notes.context_notes),
    ]
    return ReaderSegment(
        id=output.segment_id,
        text=output.text,
        new_gloss_ids=output.glosses.new_gloss_ids,
        tokens=tokens,
        notes=tuple(notes),
    )


def _grammar_notes_to_reader(notes: tuple[GrammarNoteItem, ...]) -> tuple[ReaderNote, ...]:
    return tuple(
        ReaderNote(
            id=note.id,
            type="grammar",
            anchor_token_ids=note.anchor_token_ids,
            body=note.body,
        )
        for note in notes
    )


def _context_notes_to_reader(notes: tuple[ContextNoteItem, ...]) -> tuple[ReaderNote, ...]:
    return tuple(
        ReaderNote(
            id=note.id,
            type="context",
            anchor_token_ids=note.anchor_token_ids,
            body=note.body,
            sources=tuple(_citation_to_reader_source(source) for source in note.sources),
        )
        for note in notes
    )


def _citation_to_reader_source(citation: NoteCitation) -> ReaderNoteSource:
    return ReaderNoteSource(label=citation.label, detail=citation.excerpt)


def _reader_source_from_dict(source: dict[str, object]) -> ReaderNoteSource:
    detail_value = source.get("detail", "")
    if not detail_value:
        detail_value = source.get("excerpt", "")
    return ReaderNoteSource(label=str(source.get("label", "")), detail=str(detail_value))


def _lowest_start_token_id(output: CompiledSegmentInputs) -> str:
    if not output.tokenization.tokens:
        return ""
    return min(output.tokenization.tokens, key=lambda token: token.start).id


def _fold_paragraph_context_notes(
    draft: ParagraphDraft,
    segments: tuple[ReaderSegment, ...],
    outputs_by_id: dict[SegmentId, CompiledSegmentInputs],
) -> tuple[ReaderSegment, ...]:
    if not draft.paragraph_context_notes:
        return segments

    segment_index = {segment.id: index for index, segment in enumerate(segments)}
    updated = list(segments)

    for note_dict in draft.paragraph_context_notes:
        anchor_segment_ids = note_dict.get("anchorSegmentIds", ())
        if not isinstance(anchor_segment_ids, (list, tuple)) or not anchor_segment_ids:
            continue
        target_segment_id = segment_id(str(anchor_segment_ids[0]))
        if target_segment_id not in segment_index:
            continue

        output = outputs_by_id[target_segment_id]
        anchor_token_id = _lowest_start_token_id(output)
        sources_raw = note_dict.get("sources", ())
        sources: tuple[ReaderNoteSource, ...] = ()
        if isinstance(sources_raw, (list, tuple)):
            sources = tuple(
                _reader_source_from_dict(source)
                if isinstance(source, dict)
                else ReaderNoteSource(label=str(source), detail="")
                for source in sources_raw
            )

        reader_note = ReaderNote(
            id=str(note_dict["id"]),
            type="context",
            anchor_token_ids=(anchor_token_id,),
            body=str(note_dict.get("body", "")),
            sources=sources,
        )
        index = segment_index[target_segment_id]
        segment = updated[index]
        updated[index] = segment.model_copy(update={"notes": segment.notes + (reader_note,)})

    return tuple(updated)
