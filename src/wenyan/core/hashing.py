import hashlib

from wenyan_models.domain.ids import ContentHash, parse_content_hash


def sha256_text(text: str) -> ContentHash:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return parse_content_hash(f"sha256:{digest}")
