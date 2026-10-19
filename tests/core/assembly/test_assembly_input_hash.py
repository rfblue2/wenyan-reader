from wenyan.core.assembly.state import SegmentOutputs, assembly_input_hash
from wenyan_models.artifacts.paragraph import ParagraphDraft
from wenyan_models.artifacts.segment import (
    ContextNotesArtifact,
    GlossesArtifact,
    GrammarNotesArtifact,
    TokenizationArtifact,
)
from wenyan_models.domain.ids import segment_id


def _minimal_segment_outputs(
    seg,
    *,
    token_id: str = "3723a8d9-6621-40e7-b444-2fcb3dcbcdcb",
    gloss_id: str = "7d0d9c78-8307-4f11-9352-63b5d74af0fd",
) -> SegmentOutputs:
    return SegmentOutputs(
        segment_id=seg,
        tokenization=TokenizationArtifact.model_validate(
            {
                "segmentId": str(seg),
                "model": "test",
                "inputHash": "sha256:t",
                "attempts": 1,
                "text": "孟子見梁惠王。",
                "tokens": [{"id": token_id, "surface": "孟子", "start": 0, "end": 2}],
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
                "grammarNotes": [],
            }
        ),
        context_notes=ContextNotesArtifact.model_validate(
            {
                "segmentId": str(seg),
                "model": "test",
                "inputHash": "sha256:cn",
                "attempts": 1,
                "contextNotes": [],
            }
        ),
    )


def test_assembly_input_hash_changes_when_segment_artifact_changes() -> None:
    seg = segment_id("d70e05cc-a271-43e6-9abd-40c97c83bb96")
    draft = ParagraphDraft.model_validate(
        {
            "paragraphId": "c777d984-afd6-4a31-aa34-2d26d29fb445",
            "model": "test",
            "inputHash": "sha256:test",
            "attempts": 1,
            "segments": [{"id": str(seg), "text": "孟子見梁惠王。"}],
        }
    )
    baseline = _minimal_segment_outputs(seg)
    changed = _minimal_segment_outputs(
        seg,
        gloss_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
    )

    assert assembly_input_hash(draft, (baseline,)) != assembly_input_hash(draft, (changed,))
