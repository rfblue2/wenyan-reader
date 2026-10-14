from wenyan.core.gloss.filter_candidates import filter_candidates_by_token_surfaces
from wenyan_models.artifacts.segment import GlossEntry, TokenizationArtifact


def test_keeps_entries_whose_surface_appears_on_a_token() -> None:
    tokenization = TokenizationArtifact.model_validate(
        {
            "segmentId": "00000000-0000-4000-8000-000000000001",
            "model": "mock",
            "inputHash": "sha256:x",
            "attempts": 1,
            "text": "將聽",
            "tokens": [
                {"id": "t1", "surface": "將", "start": 0, "end": 1},
                {"id": "t2", "surface": "聽", "start": 1, "end": 2},
            ],
        },
    )
    candidates = (
        GlossEntry(id="g-jiang", surface="將", pinyin="jiāng", gloss="will"),
        GlossEntry(id="g-guo", surface="國", pinyin="guó", gloss="state"),
        GlossEntry(id="g-ting", surface="聽", pinyin="tīng", gloss="hear"),
    )
    filtered = filter_candidates_by_token_surfaces(candidates, tokenization)
    assert {e.id for e in filtered} == {"g-jiang", "g-ting"}


def test_returns_empty_when_no_surface_overlap() -> None:
    tokenization = TokenizationArtifact.model_validate(
        {
            "segmentId": "00000000-0000-4000-8000-000000000001",
            "model": "mock",
            "inputHash": "sha256:x",
            "attempts": 1,
            "text": "兵",
            "tokens": [{"id": "t1", "surface": "兵", "start": 0, "end": 1}],
        },
    )
    candidates = (GlossEntry(id="g-guo", surface="國", pinyin="guó", gloss="state"),)
    assert filter_candidates_by_token_surfaces(candidates, tokenization) == ()
