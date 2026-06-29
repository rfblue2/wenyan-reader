import pytest
from pydantic import ValidationError

from wenyan_models.artifacts.segment import (
    ContextNoteItem,
    GrammarNoteItem,
    GrammarNotesArtifact,
    NoteCitation,
)


def test_grammar_note_item_parses_design_example() -> None:
    note = GrammarNoteItem.model_validate(
        {
            "id": "6f79c527-259a-4e7e-8c51-8c2f71d801c2",
            "anchorTokenIds": ["3723a8d9-6621-40e7-b444-2fcb3dcbcdcb"],
            "body": "見 here is used in the sense of 'had an audience with' a superior.",
        },
    )
    assert note.anchor_token_ids == ("3723a8d9-6621-40e7-b444-2fcb3dcbcdcb",)


def test_grammar_note_item_rejects_sources_field() -> None:
    with pytest.raises(ValidationError):
        GrammarNoteItem.model_validate(
            {
                "id": "6f79c527-259a-4e7e-8c51-8c2f71d801c2",
                "anchorTokenIds": ["3723a8d9-6621-40e7-b444-2fcb3dcbcdcb"],
                "body": "Example.",
                "sources": [],
            },
        )


def test_context_note_item_parses_design_example() -> None:
    note = ContextNoteItem.model_validate(
        {
            "id": "8a12b634-370b-51f8-9d63-a3e4e812d3d4",
            "anchorTokenIds": ["3723a8d9-6621-40e7-b444-2fcb3dcbcdcb"],
            "body": "Mencius is being introduced in an audience with a ruler.",
            "sources": [
                {
                    "url": "https://example.com/mencius-1a1",
                    "label": "Mencius 1A1",
                    "excerpt": "孟子見梁惠王。",
                    "accessedAt": "2026-06-28",
                },
            ],
        },
    )
    assert note.sources[0].label == "Mencius 1A1"
    assert note.sources[0].accessed_at == "2026-06-28"


def test_grammar_notes_artifact_uses_grammar_note_items() -> None:
    artifact = GrammarNotesArtifact.model_validate(
        {
            "segmentId": "d70e05cc-a271-43e6-9abd-40c97c83bb96",
            "model": "editor",
            "inputHash": "sha256:test",
            "attempts": 1,
            "grammarNotes": [
                {
                    "id": "6f79c527-259a-4e7e-8c51-8c2f71d801c2",
                    "anchorTokenIds": ["3723a8d9-6621-40e7-b444-2fcb3dcbcdcb"],
                    "body": "Example grammar note.",
                },
            ],
        },
    )
    assert isinstance(artifact.grammar_notes[0], GrammarNoteItem)


def test_note_citation_requires_label_and_excerpt() -> None:
    NoteCitation.model_validate(
        {
            "label": "Shiji",
            "excerpt": "Quoted passage.",
        },
    )
