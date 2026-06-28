from typing import Protocol

from wenyan_models.domain.ids import DocumentId, Slug
from wenyan_models.sources import DocumentYaml, RegistryEntry


class SourceRegistry(Protocol):
    def resolve(self, id_or_slug: str) -> RegistryEntry: ...

    def assign_document_id(self, slug: Slug, document_id: DocumentId) -> None: ...

    def load_document_yaml(self, slug: Slug) -> DocumentYaml: ...
