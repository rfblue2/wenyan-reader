from wenyan_models.artifacts.segment import (
    NoteItem,
    TokenItem,
    TokenizationArtifact,
)
from wenyan.core.notes.normalize_notes import normalize_grammar_notes


def _tokenization() -> TokenizationArtifact:
    return TokenizationArtifact(
        segmentId="seg-1",
        model="mock",
        inputHash="sha256:test",
        attempts=1,
        text="國之大事",
        tokens=(
            TokenItem(id="t1", surface="國", start=0, end=1),
            TokenItem(id="t2", surface="之", start=1, end=2),
            TokenItem(id="t3", surface="大事", start=2, end=4),
        ),
    )


def test_normalize_grammar_notes_drops_empty_body_and_invalid_anchors() -> None:
    tokenization = _tokenization()
    notes = (
        NoteItem(id="n1", anchorTokenIds=("t2",), body=""),
        NoteItem(id="n2", anchorTokenIds=(), body="Missing anchors."),
        NoteItem(id="n3", anchorTokenIds=("missing",), body="Bad anchor."),
        NoteItem(id="n4", anchorTokenIds=("t2",), body="之 links modifier to head."),
    )

    normalized = normalize_grammar_notes(notes, tokenization)

    assert len(normalized) == 1
    assert normalized[0].id == "n4"
