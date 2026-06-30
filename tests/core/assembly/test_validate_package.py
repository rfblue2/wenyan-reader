from wenyan.core.assembly.compile_paragraph import compile_paragraph_package
from wenyan.core.assembly.load_segment_outputs import CompiledSegmentInputs
from wenyan.core.assembly.validate_package import validate_paragraph_package
from wenyan_models.artifacts.paragraph import ParagraphDraft
from wenyan_models.artifacts.segment import (
    ContextNotesArtifact,
    GlossesArtifact,
    GrammarNotesArtifact,
    TokenizationArtifact,
)
from wenyan_models.domain.enums import ValidationStatus
from wenyan_models.domain.ids import SegmentId, segment_id


def _minimal_segment_outputs(
    seg: SegmentId,
    *,
    token_id: str = "3723a8d9-6621-40e7-b444-2fcb3dcbcdcb",
    gloss_id: str = "7d0d9c78-8307-4f11-9352-63b5d74af0fd",
    extra_tokens: tuple[dict[str, object], ...] = (),
    grammar_notes: tuple[dict[str, object], ...] = (),
    context_notes: tuple[dict[str, object], ...] = (),
    gloss_decisions: list[dict[str, object]] | None = None,
) -> CompiledSegmentInputs:
    tokens = [{"id": token_id, "surface": "孟子", "start": 0, "end": 2}, *extra_tokens]
    if gloss_decisions is None:
        gloss_decisions = [
            {"tokenId": token_id, "glossId": gloss_id, "decision": "reuse-existing"}
        ]
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
                "glossDecisions": gloss_decisions,
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


def test_validate_package_passes_minimal_compiled_package() -> None:
    seg = segment_id("d70e05cc-a271-43e6-9abd-40c97c83bb96")
    token_id = "3723a8d9-6621-40e7-b444-2fcb3dcbcdcb"
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
    validation = validate_paragraph_package(draft, outputs, package)

    assert validation.status == ValidationStatus.PASSED
    assert validation.paragraph_id == draft.paragraph_id
    assert validation.checks == ()


def test_validate_package_rejects_missing_gloss_on_token() -> None:
    seg = segment_id("d70e05cc-a271-43e6-9abd-40c97c83bb96")
    token_id = "3723a8d9-6621-40e7-b444-2fcb3dcbcdcb"
    extra_token_id = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
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
            extra_tokens=(
                {"id": extra_token_id, "surface": "見", "start": 2, "end": 3},
            ),
            gloss_decisions=[
                {
                    "tokenId": token_id,
                    "glossId": "7d0d9c78-8307-4f11-9352-63b5d74af0fd",
                    "decision": "reuse-existing",
                }
            ],
        ),
    )
    package = compile_paragraph_package(draft, outputs)
    validation = validate_paragraph_package(draft, outputs, package)

    assert validation.status == ValidationStatus.FAILED
    assert any(check.code == "token-gloss-coverage" for check in validation.checks)
