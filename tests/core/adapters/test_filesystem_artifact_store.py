from pydantic import BaseModel, ConfigDict

from wenyan.core.adapters.filesystem_artifact_store import FilesystemArtifactStore
from wenyan.core.ports.artifact_ref import normalized_document_ref
from wenyan_models.domain.ids import document_id


class StubArtifact(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    message: str


def test_round_trip_write_and_read(tmp_path) -> None:
    store = FilesystemArtifactStore(tmp_path)
    doc = document_id("9ad841a6-f20f-4f43-9805-166ab2d98e7f")
    ref = normalized_document_ref(doc)
    payload = StubArtifact(message="hello")

    assert not store.exists(ref)
    store.write(ref, payload, dry_run=False)
    assert store.exists(ref)

    loaded = store.read(ref, StubArtifact)
    assert loaded == payload


def test_dry_run_does_not_write(tmp_path) -> None:
    store = FilesystemArtifactStore(tmp_path)
    doc = document_id("9ad841a6-f20f-4f43-9805-166ab2d98e7f")
    ref = normalized_document_ref(doc)

    store.write(ref, StubArtifact(message="hello"), dry_run=True)
    assert not store.exists(ref)
