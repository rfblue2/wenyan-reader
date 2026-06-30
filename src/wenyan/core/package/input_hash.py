import json

from wenyan.core.adapters.hashing import sha256_text
from wenyan_models.artifacts.glossary import GlossaryDraft
from wenyan_models.domain.ids import ContentHash


def package_input_hash(
    *,
    normalized_hash: ContentHash,
    glossary: GlossaryDraft,
    paragraph_assembly_hashes: tuple[tuple[str, str], ...],
) -> ContentHash:
    payload = {
        "normalizedHash": str(normalized_hash),
        "glossary": glossary.model_dump(by_alias=True),
        "paragraphs": dict(paragraph_assembly_hashes),
    }
    return sha256_text(json.dumps(payload, sort_keys=True, ensure_ascii=False))
