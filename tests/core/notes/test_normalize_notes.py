from wenyan_models.artifacts.segment import NoteItem, NoteSource, TokenItem, TokenizationArtifact
from wenyan.core.notes.normalize_notes import normalize_notes


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


def test_normalize_notes_drops_empty_body_and_invalid_anchors() -> None:
    tokenization = _tokenization()
    notes = (
        NoteItem(
            id="n1",
            type="grammar",
            anchorTokenIds=("t2",),
            body="",
        ),
        NoteItem(
            id="n2",
            type="grammar",
            anchorTokenIds=(),
            body="Missing anchors.",
        ),
        NoteItem(
            id="n3",
            type="grammar",
            anchorTokenIds=("missing",),
            body="Bad anchor.",
        ),
        NoteItem(
            id="n4",
            type="grammar",
            anchorTokenIds=("t2",),
            body="之 links modifier to head.",
        ),
    )

    normalized = normalize_notes(notes, tokenization)

    assert len(normalized) == 1
    assert normalized[0].id == "n4"


def test_normalize_notes_deduplicates_ids_and_filters_invalid_sources() -> None:
    tokenization = _tokenization()
    notes = (
        NoteItem(
            id="n1",
            type="context",
            anchorTokenIds=("t1",),
            body="State affairs.",
            sources=(
                NoteSource(sourceId="src-001", label="Commentary", detail=""),
                NoteSource(sourceId="missing", label="Bad", detail=""),
            ),
        ),
        NoteItem(
            id="n1",
            type="context",
            anchorTokenIds=("t3",),
            body="Duplicate id.",
        ),
    )

    normalized = normalize_notes(
        notes,
        tokenization,
        source_snippet_ids=frozenset({"src-001"}),
    )

    assert len(normalized) == 1
    assert normalized[0].anchor_token_ids == ("t1",)
    assert len(normalized[0].sources) == 1
    assert normalized[0].sources[0].source_id == "src-001"
