from wenyan_models.artifacts.segment import NoteItem, TokenizationArtifact


def normalize_grammar_notes(
    notes: tuple[NoteItem, ...],
    tokenization: TokenizationArtifact,
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
        normalized.append(note)
    return tuple(normalized)
