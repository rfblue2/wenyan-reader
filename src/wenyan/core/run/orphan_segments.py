import shutil
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from wenyan.core.adapters.paths import document_root
from wenyan.core.ports.artifact_ref import segment_input_ref
from wenyan.core.ports.artifact_store import ArtifactStore
from wenyan.core.run.work_queue import iter_segments_in_document_order
from wenyan_models.artifacts.segment import SegmentInput
from wenyan_models.domain.ids import DocumentId, SegmentId, segment_id

_DEFAULT_MODEL_CONFIG = {"frozen": True, "populate_by_name": True, "extra": "forbid"}


class OrphanSegmentItem(BaseModel):
    model_config = ConfigDict(**_DEFAULT_MODEL_CONFIG)

    segment_id: SegmentId
    path: str
    text_preview: str = ""


class PruneOrphanSegmentsResult(BaseModel):
    model_config = ConfigDict(**_DEFAULT_MODEL_CONFIG)

    dry_run: bool
    removed: tuple[OrphanSegmentItem, ...]


def find_orphan_segments(
    artifacts: ArtifactStore,
    repo_root: Path,
    document_id: DocumentId,
) -> tuple[OrphanSegmentItem, ...]:
    active = set(iter_segments_in_document_order(artifacts, document_id))
    segments_root = document_root(repo_root, document_id) / "jobs" / "segments"
    if not segments_root.is_dir():
        return ()
    orphans: list[OrphanSegmentItem] = []
    for entry in sorted(segments_root.iterdir(), key=lambda path: path.name):
        if not entry.is_dir() or entry.name.startswith("."):
            continue
        segment_id_value = segment_id(entry.name)
        if segment_id_value in active:
            continue
        orphans.append(
            OrphanSegmentItem(
                segment_id=segment_id_value,
                path=entry.relative_to(repo_root).as_posix(),
                text_preview=_segment_text_preview(artifacts, document_id, segment_id_value),
            ),
        )
    return tuple(orphans)


def prune_orphan_segments(
    artifacts: ArtifactStore,
    repo_root: Path,
    document_id: DocumentId,
    *,
    dry_run: bool,
) -> PruneOrphanSegmentsResult:
    orphans = find_orphan_segments(artifacts, repo_root, document_id)
    if not dry_run:
        for item in orphans:
            shutil.rmtree(document_root(repo_root, document_id) / "jobs" / "segments" / str(item.segment_id))
    return PruneOrphanSegmentsResult(dry_run=dry_run, removed=orphans)


def _segment_text_preview(
    artifacts: ArtifactStore,
    document_id: DocumentId,
    segment_id_value: SegmentId,
) -> str:
    input_ref = segment_input_ref(document_id, segment_id_value)
    if not artifacts.exists(input_ref):
        return ""
    segment_input = artifacts.read(input_ref, SegmentInput)
    return _preview_text(segment_input.segment_text)


def _preview_text(text: str, *, limit: int = 40) -> str:
    compact = text.replace("\n", " ").strip()
    if len(compact) <= limit:
        return compact
    return f"{compact[: limit - 1]}…"
