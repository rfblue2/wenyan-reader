from wenyan.core.adapters.hashing import sha256_text as _sha256_text
from wenyan.core.ports.content_hasher import ContentHasher
from wenyan_models.domain.ids import ContentHash


class Sha256ContentHasher(ContentHasher):
    def sha256_text(self, text: str) -> ContentHash:
        return _sha256_text(text)
