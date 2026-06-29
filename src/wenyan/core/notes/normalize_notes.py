from wenyan_models.artifacts.segment import NoteItem, NoteSource, TokenizationArtifact


def normalize_notes(
    notes: tuple[NoteItem, ...],
    tokenization: TokenizationArtifact,
    *,
    source_snippet_ids: frozenset[str] | None = None,
) -> tuple[NoteItem, ...]:
    token_ids = {token.id for token in tokenization.tokens}
    seen_note_ids: set[str] = set()
    normalized: list[NoteItem] = []
    for note in notes:
        if not note.body.strip() or not note.anchor_token_ids:
            continue
        if not all(token_id in token_ids for token_id in note.anchor_token_ids):
            continue
        if note.id in seen_note_ids:
            continue
        seen_note_ids.add(note.id)
        sources = _normalize_sources(note.sources, source_snippet_ids)
        normalized.append(note.model_copy(update={"sources": sources}))
    return tuple(normalized)


def _normalize_sources(
    sources: tuple[NoteSource, ...],
    source_snippet_ids: frozenset[str] | None,
) -> tuple[NoteSource, ...]:
    if not sources:
        return ()
    if source_snippet_ids is None:
        return sources
    return tuple(source for source in sources if source.source_id in source_snippet_ids)
