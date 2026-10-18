import shutil
from pathlib import Path

from wenyan.core.adapters.paths import document_root
from wenyan.core.ports.artifact_ref import ParagraphArtifactKind, ParagraphRef
from wenyan.core.ports.artifact_store import ArtifactStore
from wenyan.core.run.segment_pipeline import pending_segment_subjobs
from wenyan.core.run.work_queue import iter_paragraphs
from wenyan.core.status.assembly import compute_assembly_input_hash
from wenyan_models.artifacts.assembly import ParagraphAssemblyValidationArtifact
from wenyan_models.artifacts.paragraph import ParagraphDraft
from wenyan_models.domain.ids import DocumentId, ParagraphId


def _assembly_dir(
    repo_root: Path,
    document_id: DocumentId,
    paragraph_id: ParagraphId,
) -> Path:
    return document_root(repo_root, document_id) / "jobs" / "assembly" / str(paragraph_id)


def _paragraph_assembly_is_stale(
    artifacts: ArtifactStore,
    repo_root: Path,
    document_id: DocumentId,
    paragraph_id: ParagraphId,
) -> bool:
    assembly_dir = _assembly_dir(repo_root, document_id, paragraph_id)
    if not assembly_dir.is_dir():
        return False

    draft_ref = ParagraphRef(ParagraphArtifactKind.DRAFT, document_id, paragraph_id)
    if not artifacts.exists(draft_ref):
        return True

    draft = artifacts.read(draft_ref, ParagraphDraft)
    for segment in draft.segments:
        if pending_segment_subjobs(artifacts, document_id, segment.id):
            return True

    validation_ref = ParagraphRef(
        ParagraphArtifactKind.ASSEMBLY_VALIDATION, document_id, paragraph_id
    )
    if not artifacts.exists(validation_ref):
        return True

    current_hash = compute_assembly_input_hash(artifacts, document_id, paragraph_id)
    if current_hash is None:
        return True

    validation = artifacts.read(validation_ref, ParagraphAssemblyValidationArtifact)
    return validation.input_hash != current_hash


def find_stale_assembly_paragraphs(
    artifacts: ArtifactStore,
    repo_root: Path,
    document_id: DocumentId,
) -> tuple[ParagraphId, ...]:
    stale: list[ParagraphId] = []
    for _chapter, paragraph in iter_paragraphs(artifacts, document_id):
        draft_ref = ParagraphRef(ParagraphArtifactKind.DRAFT, document_id, paragraph.id)
        if not artifacts.exists(draft_ref):
            continue
        if _paragraph_assembly_is_stale(artifacts, repo_root, document_id, paragraph.id):
            stale.append(paragraph.id)
    return tuple(stale)


def prune_stale_assembly(
    artifacts: ArtifactStore,
    repo_root: Path,
    document_id: DocumentId,
    *,
    dry_run: bool,
) -> tuple[str, ...]:
    removed: list[str] = []
    for paragraph_id in find_stale_assembly_paragraphs(artifacts, repo_root, document_id):
        assembly_dir = _assembly_dir(repo_root, document_id, paragraph_id)
        path = assembly_dir.relative_to(repo_root).as_posix()
        removed.append(path)
        if not dry_run:
            shutil.rmtree(assembly_dir)
    return tuple(removed)
