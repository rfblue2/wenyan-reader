from typing import Protocol

from wenyan_models.domain.ids import ContentHash


class ContentHasher(Protocol):
    def sha256_text(self, text: str) -> ContentHash: ...
