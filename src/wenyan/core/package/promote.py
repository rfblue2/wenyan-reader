import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel

from wenyan_models.domain.ids import ChapterId, DocumentId, ParagraphId
from wenyan_models.reader.document import ChapterPackage, DocumentManifest, GlossIndex
from wenyan_models.reader.paragraph import ParagraphPackage


@dataclass(frozen=True)
class ContentWrite:
    path: Path
    payload: BaseModel


def plan_content_writes(
    repo_root: Path,
    document_id: DocumentId,
    manifest: DocumentManifest,
    gloss_index: GlossIndex,
    chapter_packages: Mapping[ChapterId, ChapterPackage],
    paragraph_packages: Mapping[ParagraphId, ParagraphPackage],
) -> tuple[ContentWrite, ...]:
    """Writes each file at the path the manifest and chapter packages reference."""
    root = repo_root / "content" / "documents" / str(document_id)
    writes = [
        ContentWrite(root / "document.json", manifest),
        ContentWrite(root / manifest.gloss_index_path, gloss_index),
    ]
    for chapter_nav in manifest.chapters:
        chapter_path = root / chapter_nav.path
        chapter = chapter_packages[chapter_nav.id]
        writes.append(ContentWrite(chapter_path, chapter))
        writes.extend(
            ContentWrite(chapter_path.parent / paragraph_nav.path, paragraph_packages[paragraph_nav.id])
            for paragraph_nav in chapter.paragraphs
        )
    return tuple(writes)


def promote_content_writes(writes: Sequence[ContentWrite], *, dry_run: bool) -> None:
    if dry_run:
        return
    pending: list[tuple[Path, Path]] = []
    for write in writes:
        final_path = write.path
        temp_path = final_path.with_name(f"{final_path.name}.tmp")
        final_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path.write_text(write.payload.model_dump_json(by_alias=True), encoding="utf-8")
        pending.append((temp_path, final_path))
    for temp_path, final_path in pending:
        os.replace(temp_path, final_path)
