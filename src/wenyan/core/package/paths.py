from pathlib import Path

from wenyan_models.domain.ids import ChapterId, DocumentId, ParagraphId


def content_document_root(repo_root: Path, document_id: DocumentId) -> Path:
    return repo_root / "content" / "documents" / str(document_id)


def content_gloss_index_path(repo_root: Path, document_id: DocumentId) -> Path:
    return content_document_root(repo_root, document_id) / "glosses" / "index.json"


def content_document_manifest_path(repo_root: Path, document_id: DocumentId) -> Path:
    return content_document_root(repo_root, document_id) / "document.json"


def content_chapter_root(repo_root: Path, document_id: DocumentId, chapter_id: ChapterId) -> Path:
    return content_document_root(repo_root, document_id) / "chapters" / str(chapter_id)


def content_chapter_manifest_path(
    repo_root: Path,
    document_id: DocumentId,
    chapter_id: ChapterId,
) -> Path:
    return content_chapter_root(repo_root, document_id, chapter_id) / "chapter.json"


def content_paragraph_path(
    repo_root: Path,
    document_id: DocumentId,
    chapter_id: ChapterId,
    paragraph_id: ParagraphId,
) -> Path:
    return (
        content_chapter_root(repo_root, document_id, chapter_id)
        / "paragraphs"
        / f"{paragraph_id}.json"
    )
