from wenyan_models.artifacts.segment import (
    ContextNoteItem,
    GrammarNoteItem,
    NoteCitation,
    TokenizationArtifact,
)


def normalize_grammar_notes(
    notes: tuple[GrammarNoteItem, ...],
    tokenization: TokenizationArtifact,
) -> tuple[GrammarNoteItem, ...]:
    return _normalize_note_items(notes, tokenization)


def normalize_context_notes(
    notes: tuple[ContextNoteItem, ...],
    tokenization: TokenizationArtifact,
) -> tuple[ContextNoteItem, ...]:
    token_ids = {token.id for token in tokenization.tokens}
    seen_note_ids: set[str] = set()
    normalized: list[ContextNoteItem] = []
    for note in notes:
        if not note.body.strip() or not note.anchor_token_ids:
            continue
        if not all(token_id in token_ids for token_id in note.anchor_token_ids):
            continue
        if note.id in seen_note_ids:
            continue
        seen_note_ids.add(note.id)
        sources = _normalize_citations(note.sources)
        normalized.append(note.model_copy(update={"sources": sources}))
    return tuple(normalized)


def _normalize_note_items[T: GrammarNoteItem](
    notes: tuple[T, ...],
    tokenization: TokenizationArtifact,
) -> tuple[T, ...]:
    token_ids = {token.id for token in tokenization.tokens}
    seen_note_ids: set[str] = set()
    normalized: list[T] = []
    for note in notes:
        if not note.body.strip() or not note.anchor_token_ids:
            continue
        if not all(token_id in token_ids for token_id in note.anchor_token_ids):
            continue
        if note.id in seen_note_ids:
            continue
        seen_note_ids.add(note.id)
        normalized.append(note)
    return tuple(normalized)


def _normalize_citations(
    citations: tuple[NoteCitation, ...],
) -> tuple[NoteCitation, ...]:
    normalized: list[NoteCitation] = []
    for citation in citations:
        if not citation.label.strip() or not citation.excerpt.strip():
            continue
        normalized.append(citation)
    return tuple(normalized)
