from wenyan.core.gloss.glossary_draft import normalize_gloss_reuse
from wenyan_models.artifacts.segment import (
    GlossDecision,
    GlossEntry,
    GlossesArtifact,
    TokenItem,
    TokenizationArtifact,
)


def test_normalize_gloss_reuse_repoints_duplicate_sense() -> None:
    existing = GlossEntry(
        id="existing-bu",
        surface="不",
        pinyin="bù",
        gloss="not; no",
    )
    tokenization = TokenizationArtifact.model_validate(
        {
            "segmentId": "00000000-0000-4000-8000-000000000001",
            "model": "mock",
            "inputHash": "sha256:tokenization",
            "attempts": 1,
            "text": "不可",
            "tokens": [
                {
                    "id": "token-bu",
                    "surface": "不",
                    "start": 0,
                    "end": 1,
                },
            ],
        },
    )
    glosses = GlossesArtifact.model_validate(
        {
            "segmentId": "00000000-0000-4000-8000-000000000001",
            "model": "mock",
            "inputHash": "sha256:glosses",
            "attempts": 1,
            "glossDecisions": [
                {
                    "tokenId": "token-bu",
                    "glossId": "new-bu",
                    "decision": "create-new",
                },
            ],
            "newGlossIds": ["new-bu"],
            "newGlosses": [
                {
                    "id": "new-bu",
                    "surface": "不",
                    "pinyin": "bù",
                    "gloss": "not; no",
                },
            ],
        },
    )

    normalized = normalize_gloss_reuse(glosses, tokenization, (existing,))

    assert normalized.gloss_decisions == (
        GlossDecision.model_validate(
            {
                "tokenId": "token-bu",
                "glossId": "existing-bu",
                "decision": "reuse-existing",
            },
        ),
    )
    assert normalized.new_glosses == ()
    assert normalized.new_gloss_ids == ()


def test_normalize_gloss_reuse_keeps_distinct_sense() -> None:
    existing = GlossEntry(
        id="existing-jiang-future",
        surface="將",
        pinyin="jiāng",
        gloss="will; shall",
    )
    tokenization = TokenizationArtifact.model_validate(
        {
            "segmentId": "00000000-0000-4000-8000-000000000002",
            "model": "mock",
            "inputHash": "sha256:tokenization",
            "attempts": 1,
            "text": "四曰將",
            "tokens": [
                {
                    "id": "token-jiang",
                    "surface": "將",
                    "start": 2,
                    "end": 3,
                },
            ],
        },
    )
    glosses = GlossesArtifact.model_validate(
        {
            "segmentId": "00000000-0000-4000-8000-000000000002",
            "model": "mock",
            "inputHash": "sha256:glosses",
            "attempts": 1,
            "glossDecisions": [
                {
                    "tokenId": "token-jiang",
                    "glossId": "new-jiang-general",
                    "decision": "create-new",
                },
            ],
            "newGlossIds": ["new-jiang-general"],
            "newGlosses": [
                {
                    "id": "new-jiang-general",
                    "surface": "將",
                    "pinyin": "jiàng",
                    "gloss": "general; commander",
                },
            ],
        },
    )

    normalized = normalize_gloss_reuse(glosses, tokenization, (existing,))

    assert normalized.gloss_decisions[0].decision == "create-new"
    assert normalized.gloss_decisions[0].gloss_id == "new-jiang-general"
    assert len(normalized.new_glosses) == 1
