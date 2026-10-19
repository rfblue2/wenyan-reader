import shutil
from pathlib import Path

from wenyan.core.adapters.paths import document_root
from wenyan.core.assembly.state import AssemblyState, ParagraphAssembly, inspect_paragraph_assembly
from wenyan.core.ports.artifact_store import ArtifactStore
from wenyan.core.run.work_queue import iter_paragraphs
from wenyan_models.domain.ids import DocumentId, ParagraphId


def _assembly_dir(
    repo_root: Path,
    document_id: DocumentId,
    paragraph_id: ParagraphId,
) -> Path:
    return document_root(repo_root, document_id) / "jobs" / "assembly" / str(paragraph_id)


def find_stale_assembly_paragraphs(
    artifacts: ArtifactStore,
    repo_root: Path,
    document_id: DocumentId,
) -> tuple[ParagraphId, ...]:
    """Paragraphs whose assembly directory holds neither a current package nor a current failed validation."""
    stale: list[ParagraphId] = []
    for _chapter, paragraph in iter_paragraphs(artifacts, document_id):
        if not _assembly_dir(repo_root, document_id, paragraph.id).is_dir():
            continue
        match inspect_paragraph_assembly(artifacts, document_id, paragraph.id):
            case None | ParagraphAssembly(state=AssemblyState.CURRENT | AssemblyState.FAILED):
                continue
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
