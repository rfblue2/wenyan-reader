import shutil
from pathlib import Path

from pydantic import BaseModel

from wenyan.core.adapters.paths import document_root
from wenyan.core.run.work_queue import iter_segments_in_document_order, segment_text_preview
from wenyan.core.ports.artifact_store import ArtifactStore
from wenyan_models.artifacts.base import DEFAULT_ARTIFACT_CONFIG
from wenyan_models.domain.ids import DocumentId, SegmentId, segment_id


class OrphanSegmentItem(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    segment_id: SegmentId
    path: str
    text_preview: str = ""


class PruneOrphanSegmentsResult(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

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
                text_preview=segment_text_preview(artifacts, document_id, segment_id_value, ""),
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
