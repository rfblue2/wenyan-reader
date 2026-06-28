import hashlib
from pathlib import Path

from wenyan_models.domain.ids import ContentHash, parse_content_hash


def sha256_text(text: str) -> ContentHash:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return parse_content_hash(f"sha256:{digest}")


def sha256_file(path: Path, *, chunk_size: int = 1024 * 1024) -> ContentHash:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return parse_content_hash(f"sha256:{digest.hexdigest()}")
