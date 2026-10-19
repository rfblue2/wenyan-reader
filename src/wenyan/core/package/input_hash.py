import json
from collections.abc import Mapping

from wenyan.core.hashing import sha256_text
from wenyan_models.artifacts.glossary import GlossaryDraft
from wenyan_models.domain.ids import ContentHash, ParagraphId


def package_input_hash(
    *,
    normalized_hash: ContentHash,
    glossary: GlossaryDraft,
    paragraph_assembly_hashes: Mapping[ParagraphId, ContentHash],
) -> ContentHash:
    payload = {
        "normalizedHash": normalized_hash,
        "glossary": glossary.model_dump(by_alias=True),
        "paragraphs": dict(paragraph_assembly_hashes),
    }
    return sha256_text(json.dumps(payload, sort_keys=True, ensure_ascii=False))
