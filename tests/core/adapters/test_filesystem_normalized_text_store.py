from pathlib import Path

from wenyan.core.adapters.filesystem_artifact_store import FilesystemArtifactStore
from wenyan.core.adapters.filesystem_normalized_text_store import FilesystemNormalizedTextStore
from wenyan.core.ports.artifact_ref import normalized_document_ref
from wenyan_models.artifacts.normalized import NormalizedDocument
from wenyan_models.domain.ids import document_id
from wenyan_models.sources import DocumentYaml


def test_write_from_source_creates_sidecar_and_manifest(tmp_path: Path) -> None:
    source_dir = tmp_path / "sources" / "documents" / "sample"
    source_dir.mkdir(parents=True)
    (source_dir / "source.txt").write_text("hello", encoding="utf-8")
    artifacts = FilesystemArtifactStore(tmp_path)
    store = FilesystemNormalizedTextStore(tmp_path, artifacts)
    doc = document_id("9ad841a6-f20f-4f43-9805-166ab2d98e7f")
    manifest = store.write_from_source(
        doc,
        "Sample",
        source_dir / "source.txt",
        DocumentYaml.model_validate({"title": "Sample", "normalization": {"encoding": "utf-8"}}),
    )
    assert manifest.character_count == 6
    assert store.text_path(doc).read_text(encoding="utf-8") == "hello\n"
    assert store.read_slice(doc, 0, 5) == "hello"
    assert store.verify_hash(doc, manifest.normalized_hash)
    loaded = artifacts.read(normalized_document_ref(doc), NormalizedDocument)
    assert loaded.normalized_hash == manifest.normalized_hash
