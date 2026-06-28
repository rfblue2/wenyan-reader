import os
from pathlib import Path

from wenyan.core.adapters.hashing import sha256_file
from wenyan.core.adapters.paths import artifact_path, document_root, normalized_text_path
from wenyan.core.adapters.streaming_normalizer import normalize_source_to_file
from wenyan.core.adapters.text_slice import read_text_slice
from wenyan.core.ports.artifact_ref import ArtifactRef, normalized_document_ref
from wenyan.core.ports.artifact_store import ArtifactStore
from wenyan.core.ports.normalized_text_store import NormalizedTextStore
from wenyan_models.artifacts.normalized import NormalizedDocument
from wenyan_models.domain.enums import ArtifactKind
from wenyan_models.domain.ids import ContentHash, DocumentId
from wenyan_models.sources import DocumentYaml


class FilesystemNormalizedTextStore(NormalizedTextStore):
    def __init__(self, repo_root: Path, artifacts: ArtifactStore) -> None:
        self._repo_root = repo_root
        self._artifacts = artifacts

    def text_path(self, document_id: DocumentId) -> Path:
        return normalized_text_path(self._repo_root, document_id)

    def character_count(self, document_id: DocumentId) -> int:
        return self._manifest(document_id).character_count

    def read_slice(self, document_id: DocumentId, start: int, end: int) -> str:
        manifest = self._manifest(document_id)
        path = self._resolve_text_path(document_id, manifest.text_path)
        return read_text_slice(path, manifest.text_index, start, end)

    def verify_hash(self, document_id: DocumentId, expected: ContentHash) -> bool:
        manifest = self._manifest(document_id)
        path = self._resolve_text_path(document_id, manifest.text_path)
        return sha256_file(path) == expected

    def write_from_source(
        self,
        document_id: DocumentId,
        title: str,
        source_path: Path,
        metadata: DocumentYaml,
    ) -> NormalizedDocument:
        punctuation_policy = "preserve-source"
        encoding = "utf-8"
        if metadata.normalization:
            punctuation_policy = str(
                metadata.normalization.get("punctuationPolicy", punctuation_policy),
            )
            encoding = str(metadata.normalization.get("encoding", encoding))
        text_path = normalized_text_path(self._repo_root, document_id)
        result = normalize_source_to_file(source_path, text_path)
        manifest = NormalizedDocument.model_validate(
            {
                "documentId": str(document_id),
                "title": title,
                "sourceHash": str(result.source_hash),
                "normalizedHash": str(result.normalized_hash),
                "textPath": "normalized-text.txt",
                "characterCount": result.character_count,
                "textIndex": result.text_index.model_dump(by_alias=True),
                "normalization": {
                    "encoding": encoding,
                    "punctuationPolicy": punctuation_policy,
                    "notes": [],
                },
            },
        )
        self._promote_manifest(document_id, manifest)
        return manifest

    def _manifest(self, document_id: DocumentId) -> NormalizedDocument:
        return self._artifacts.read(normalized_document_ref(document_id), NormalizedDocument)

    def _resolve_text_path(self, document_id: DocumentId, relative_path: str) -> Path:
        root = document_root(self._repo_root, document_id)
        return root / relative_path

    def _promote_manifest(self, document_id: DocumentId, manifest: NormalizedDocument) -> None:
        ref = normalized_document_ref(document_id)
        final_path = artifact_path(self._repo_root, ref)
        temp_path = final_path.with_name(f"{final_path.name}.tmp")
        final_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path.write_text(manifest.model_dump_json(by_alias=True), encoding="utf-8")
        os.replace(temp_path, final_path)

    def sidecar_exists(self, document_id: DocumentId) -> bool:
        return self.text_path(document_id).is_file()

    def manifest_ref(self, document_id: DocumentId) -> ArtifactRef:
        return normalized_document_ref(document_id)

    @staticmethod
    def artifact_kind() -> ArtifactKind:
        return ArtifactKind.NORMALIZED_DOCUMENT
