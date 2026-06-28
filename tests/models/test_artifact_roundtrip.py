from wenyan_models.artifacts import ChapterProposal, NormalizedDocument
from wenyan_models.domain.enums import ValidationStatus
from wenyan_models.domain.ids import chapter_id, document_id, parse_content_hash


def test_normalized_document_round_trip() -> None:
    payload = {
        "documentId": "9ad841a6-f20f-4f43-9805-166ab2d98e7f",
        "title": "孙子兵法",
        "sourceHash": "sha256:abc",
        "normalizedHash": "sha256:def",
        "textPath": "normalized-text.txt",
        "characterCount": 4,
        "textIndex": {"stride": 65536, "byteOffsets": [0]},
        "normalization": {
            "encoding": "utf-8",
            "punctuationPolicy": "preserve-source",
            "notes": [],
        },
    }
    model = NormalizedDocument.model_validate(payload)
    restored = NormalizedDocument.model_validate(model.model_dump(by_alias=True))
    assert restored == model
    assert restored.document_id == document_id("9ad841a6-f20f-4f43-9805-166ab2d98e7f")


def test_chapter_proposal_round_trip() -> None:
    payload = {
        "documentId": "9ad841a6-f20f-4f43-9805-166ab2d98e7f",
        "model": "claude-opus-4-8",
        "inputHash": "sha256:input",
        "attempts": 1,
        "sourceHash": "sha256:source",
        "chapters": [
            {
                "id": "6c708ee9-95c0-4d23-8a4f-8cb5fd62c605",
                "title": "始計第一",
                "start": 0,
                "end": 10,
                "rationale": "heading",
            }
        ],
    }
    model = ChapterProposal.model_validate(payload)
    restored = ChapterProposal.model_validate(model.model_dump(by_alias=True))
    assert restored == model
    assert restored.chapters[0].id == chapter_id("6c708ee9-95c0-4d23-8a4f-8cb5fd62c605")
    assert restored.input_hash == parse_content_hash("sha256:input")


def test_span_validation_artifact_round_trip() -> None:
    from wenyan_models.artifacts.structure import SpanValidationArtifact

    payload = {"status": ValidationStatus.PASSED, "checks": []}
    model = SpanValidationArtifact.model_validate(payload)
    assert model.status == ValidationStatus.PASSED
