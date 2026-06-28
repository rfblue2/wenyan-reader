import json
import os
from collections.abc import Sequence
from pathlib import Path

from pydantic import BaseModel

from wenyan.core.adapters.paths import artifact_path
from wenyan.core.ports.artifact_ref import ArtifactRef
from wenyan.core.ports.artifact_store import ArtifactWrite


class FilesystemArtifactStore:
    def __init__(self, repo_root: Path) -> None:
        self._repo_root = repo_root

    def exists(self, ref: ArtifactRef) -> bool:
        return artifact_path(self._repo_root, ref).is_file()

    def read[T: BaseModel](self, ref: ArtifactRef, model: type[T]) -> T:
        path = artifact_path(self._repo_root, ref)
        data = json.loads(path.read_text(encoding="utf-8"))
        return model.model_validate(data)

    def write[T: BaseModel](self, ref: ArtifactRef, payload: T, *, dry_run: bool) -> None:
        if dry_run:
            return
        self._promote(ref, payload.model_dump_json(by_alias=True))

    def write_batch(self, writes: Sequence[ArtifactWrite], *, dry_run: bool) -> None:
        if dry_run:
            return
        pending: list[tuple[Path, Path, str]] = []
        for write in writes:
            final_path = artifact_path(self._repo_root, write.ref)
            temp_path = self._temp_path(final_path)
            final_path.parent.mkdir(parents=True, exist_ok=True)
            content = write.payload.model_dump_json(by_alias=True)
            temp_path.write_text(content, encoding="utf-8")
            pending.append((temp_path, final_path, content))
        for temp_path, final_path, _ in pending:
            os.replace(temp_path, final_path)

    def delete(self, ref: ArtifactRef) -> None:
        path = artifact_path(self._repo_root, ref)
        path.unlink(missing_ok=True)

    def _promote(self, ref: ArtifactRef, content: str) -> None:
        final_path = artifact_path(self._repo_root, ref)
        temp_path = self._temp_path(final_path)
        final_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path.write_text(content, encoding="utf-8")
        os.replace(temp_path, final_path)

    @staticmethod
    def _temp_path(final_path: Path) -> Path:
        return final_path.with_name(f"{final_path.name}.tmp")
