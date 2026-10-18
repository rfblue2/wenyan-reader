from pathlib import Path

from wenyan_models.domain.ids import DocumentId


def document_root(repo_root: Path, document_id: DocumentId) -> Path:
    return repo_root / "preprocess" / "documents" / str(document_id)


def normalized_text_path(repo_root: Path, document_id: DocumentId) -> Path:
    return document_root(repo_root, document_id) / "normalized-text.txt"
