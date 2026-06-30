from wenyan.core.assembly.compile_paragraph import compile_paragraph_package
from wenyan.core.assembly.load_segment_outputs import CompiledSegmentInputs
from wenyan_models.artifacts.paragraph import ParagraphDraft
from wenyan_models.artifacts.segment import (
    ContextNotesArtifact,
    GlossesArtifact,
    GrammarNotesArtifact,
    TokenizationArtifact,
)
from wenyan_models.domain.ids import SegmentId, segment_id


def _minimal_segment_outputs(
    seg: SegmentId,
    *,
    token_id: str = "3723a8d9-6621-40e7-b444-2fcb3dcbcdcb",
    gloss_id: str = "7d0d9c78-8307-4f11-9352-63b5d74af0fd",
    extra_tokens: tuple[dict[str, object], ...] = (),
    grammar_notes: tuple[dict[str, object], ...] = (),
    context_notes: tuple[dict[str, object], ...] = (),
) -> CompiledSegmentInputs:
    tokens = [{"id": token_id, "surface": "孟子", "start": 0, "end": 2}, *extra_tokens]
    return CompiledSegmentInputs(
        segment_id=seg,
        text="孟子見梁惠王。",
        tokenization=TokenizationArtifact.model_validate(
            {
                "segmentId": str(seg),
                "model": "test",
                "inputHash": "sha256:t",
                "attempts": 1,
                "text": "孟子見梁惠王。",
                "tokens": tokens,
            }
        ),
        glosses=GlossesArtifact.model_validate(
            {
                "segmentId": str(seg),
                "model": "test",
                "inputHash": "sha256:g",
                "attempts": 1,
                "glossDecisions": [
                    {"tokenId": token_id, "glossId": gloss_id, "decision": "reuse-existing"}
                ],
                "newGlossIds": [gloss_id],
                "newGlosses": [],
            }
        ),
        grammar_notes=GrammarNotesArtifact.model_validate(
            {
                "segmentId": str(seg),
                "model": "test",
                "inputHash": "sha256:gr",
                "attempts": 1,
                "grammarNotes": list(grammar_notes),
            }
        ),
        context_notes=ContextNotesArtifact.model_validate(
            {
                "segmentId": str(seg),
                "model": "test",
                "inputHash": "sha256:cn",
                "attempts": 1,
                "contextNotes": list(context_notes),
            }
        ),
    )


def test_compile_joins_tokens_glosses_and_notes() -> None:
    seg = segment_id("d70e05cc-a271-43e6-9abd-40c97c83bb96")
    token_id = "3723a8d9-6621-40e7-b444-2fcb3dcbcdcb"
    gloss_id = "7d0d9c78-8307-4f11-9352-63b5d74af0fd"
    draft = ParagraphDraft.model_validate(
        {
            "paragraphId": "c777d984-afd6-4a31-aa34-2d26d29fb445",
            "model": "test",
            "inputHash": "sha256:test",
            "attempts": 1,
            "segments": [{"id": str(seg), "text": "孟子見梁惠王。"}],
        }
    )
    outputs = (
        _minimal_segment_outputs(
            seg,
            grammar_notes=(
                {
                    "id": "6f79c527-259a-4e7e-8c51-8c2f71d801c2",
                    "anchorTokenIds": [token_id],
                    "body": "Grammar note.",
                },
            ),
            context_notes=(
                {
                    "id": "8a12b634-370b-51f8-9d63-a3e4e812d3d4",
                    "anchorTokenIds": [token_id],
                    "body": "Context note.",
                    "sources": [{"label": "Mencius 1A1", "excerpt": "detail text"}],
                },
            ),
        ),
    )
    package = compile_paragraph_package(draft, outputs)
    segment = package.segments[0]
    assert segment.tokens[0].gloss_id == gloss_id
    assert segment.new_gloss_ids == (gloss_id,)
    assert len(segment.notes) == 2
    assert segment.notes[0].type == "grammar"
    assert segment.notes[1].type == "context"
    assert segment.notes[1].sources[0].detail == "detail text"


def test_compile_folds_paragraph_context_notes() -> None:
    seg = segment_id("d70e05cc-a271-43e6-9abd-40c97c83bb96")
    token_low = "3723a8d9-6621-40e7-b444-2fcb3dcbcdcb"
    token_high = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    para_note_id = "6f79c527-259a-4e7e-8c51-8c2f71d801c2"
    draft = ParagraphDraft.model_validate(
        {
            "paragraphId": "c777d984-afd6-4a31-aa34-2d26d29fb445",
            "model": "test",
            "inputHash": "sha256:test",
            "attempts": 1,
            "segments": [{"id": str(seg), "text": "孟子見梁惠王。"}],
            "paragraphContextNotes": [
                {
                    "id": para_note_id,
                    "anchorSegmentIds": [str(seg)],
                    "body": "Paragraph-level context.",
                    "sources": [{"label": "Mencius 1A1", "excerpt": "Passage detail."}],
                }
            ],
        }
    )
    outputs = (
        _minimal_segment_outputs(
            seg,
            extra_tokens=(
                {"id": token_high, "surface": "見", "start": 2, "end": 3},
            ),
        ),
    )
    package = compile_paragraph_package(draft, outputs)
    segment = package.segments[0]
    para_notes = [note for note in segment.notes if note.id == para_note_id]
    assert len(para_notes) == 1
    note = para_notes[0]
    assert note.type == "context"
    assert note.anchor_token_ids == (token_low,)
    assert note.body == "Paragraph-level context."
    assert note.sources[0].detail == "Passage detail."
