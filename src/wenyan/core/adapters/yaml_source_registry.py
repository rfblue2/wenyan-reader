import os
import uuid
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field

from wenyan.core.ports.source_registry import SourceRegistry
from wenyan_models.domain.ids import DocumentId, Slug, document_id, slug
from wenyan_models.sources import DocumentYaml, RegistryEntry

_DEFAULT_MODEL_CONFIG = ConfigDict(frozen=True, populate_by_name=True, extra="forbid")


class _RegistryDocument(BaseModel):
    model_config = _DEFAULT_MODEL_CONFIG

    slug: Slug
    title: str
    status: str
    document_id: DocumentId | None = Field(default=None, alias="documentId")


class _RegistryFile(BaseModel):
    model_config = _DEFAULT_MODEL_CONFIG

    documents: tuple[_RegistryDocument, ...]


class YamlSourceRegistry(SourceRegistry):
    def __init__(self, repo_root: Path) -> None:
        self._repo_root = repo_root
        self._registry_path = repo_root / "sources" / "registry.yaml"

    def resolve(self, id_or_slug: str) -> RegistryEntry:
        registry = self._load_registry()
        if _looks_like_uuid(id_or_slug):
            doc_id = document_id(id_or_slug)
            for entry in registry.documents:
                if entry.document_id == doc_id:
                    return _to_registry_entry(entry)
            raise ValueError(f"document id not found: {id_or_slug}")
        slug_value = slug(id_or_slug)
        for entry in registry.documents:
            if entry.slug == slug_value:
                return _to_registry_entry(entry)
        raise ValueError(f"document slug not found: {id_or_slug}")

    def assign_document_id(self, slug_value: Slug, document_id_value: DocumentId) -> None:
        registry = self._load_registry()
        updated: list[_RegistryDocument] = []
        found = False
        for entry in registry.documents:
            if entry.slug == slug_value:
                updated.append(
                    entry.model_copy(update={"document_id": document_id_value}),
                )
                found = True
            else:
                updated.append(entry)
        if not found:
            raise ValueError(f"document slug not found: {slug_value}")
        self._write_registry(_RegistryFile(documents=tuple(updated)))

    def load_document_yaml(self, slug_value: Slug) -> DocumentYaml:
        path = self._repo_root / "sources" / "documents" / str(slug_value) / "document.yaml"
        if not path.is_file():
            raise ValueError(f"document.yaml not found for slug: {slug_value}")
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(loaded, dict):
            raise ValueError(f"invalid document.yaml for slug: {slug_value}")
        return DocumentYaml.model_validate(loaded)

    def read_source_text(self, slug_value: Slug) -> str:
        path = self._repo_root / "sources" / "documents" / str(slug_value) / "source.txt"
        if not path.is_file():
            raise ValueError(f"source.txt not found for slug: {slug_value}")
        return path.read_text(encoding="utf-8")

    def source_slug_from_path(self, source_dir: Path) -> Slug:
        documents_root = (self._repo_root / "sources" / "documents").resolve()
        resolved = source_dir.resolve()
        if documents_root not in resolved.parents and resolved != documents_root:
            raise ValueError("ingest accepts a source directory under sources/documents/<slug>/")
        if resolved == documents_root:
            raise ValueError("ingest accepts a source directory under sources/documents/<slug>/")
        return slug(resolved.name)

    def _load_registry(self) -> _RegistryFile:
        if not self._registry_path.is_file():
            raise ValueError("sources/registry.yaml not found")
        loaded = yaml.safe_load(self._registry_path.read_text(encoding="utf-8"))
        if not isinstance(loaded, dict):
            raise ValueError("invalid sources/registry.yaml")
        return _RegistryFile.model_validate(loaded)

    def _write_registry(self, registry: _RegistryFile) -> None:
        payload = {
            "documents": [
                {
                    "slug": str(entry.slug),
                    "title": entry.title,
                    "status": entry.status,
                    **(
                        {"documentId": str(entry.document_id)}
                        if entry.document_id is not None
                        else {}
                    ),
                }
                for entry in registry.documents
            ]
        }
        temp_path = self._registry_path.with_suffix(".yaml.tmp")
        temp_path.write_text(
            yaml.safe_dump(payload, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
        os.replace(temp_path, self._registry_path)


def _to_registry_entry(entry: _RegistryDocument) -> RegistryEntry:
    return RegistryEntry(
        slug=entry.slug,
        title=entry.title,
        document_id=entry.document_id,
    )


def _looks_like_uuid(value: str) -> bool:
    try:
        uuid.UUID(value)
    except ValueError:
        return False
    return True
