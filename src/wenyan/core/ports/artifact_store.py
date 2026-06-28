from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from pydantic import BaseModel

from wenyan.core.ports.artifact_ref import ArtifactRef


@dataclass(frozen=True)
class ArtifactWrite:
    ref: ArtifactRef
    payload: BaseModel


class ArtifactStore(Protocol):
    def exists(self, ref: ArtifactRef) -> bool: ...

    def read[T: BaseModel](self, ref: ArtifactRef, model: type[T]) -> T: ...

    def write[T: BaseModel](self, ref: ArtifactRef, payload: T, *, dry_run: bool) -> None: ...

    def write_batch(self, writes: Sequence[ArtifactWrite], *, dry_run: bool) -> None: ...

    def delete(self, ref: ArtifactRef) -> None: ...
