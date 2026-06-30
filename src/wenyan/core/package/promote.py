import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel

from wenyan_models.domain.ids import ChapterId, DocumentId, ParagraphId
from wenyan_models.reader.document import ChapterPackage, DocumentManifest, GlossIndex
from wenyan_models.reader.paragraph import ParagraphPackage

from wenyan.core.package.paths import (
    content_chapter_manifest_path,
    content_document_manifest_path,
    content_gloss_index_path,
    content_paragraph_path,
)


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
    writes: list[ContentWrite] = [
        ContentWrite(content_document_manifest_path(repo_root, document_id), manifest),
        ContentWrite(content_gloss_index_path(repo_root, document_id), gloss_index),
    ]
    for chapter_id, chapter_package in chapter_packages.items():
        writes.append(
            ContentWrite(
                content_chapter_manifest_path(repo_root, document_id, chapter_id),
                chapter_package,
            ),
        )
    for paragraph_id_value, paragraph_package in paragraph_packages.items():
        chapter_id = _chapter_for_paragraph(chapter_packages, paragraph_id_value)
        writes.append(
            ContentWrite(
                content_paragraph_path(
                    repo_root,
                    document_id,
                    chapter_id,
                    paragraph_id_value,
                ),
                paragraph_package,
            ),
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


def _chapter_for_paragraph(
    chapter_packages: Mapping[ChapterId, ChapterPackage],
    paragraph_id_value: ParagraphId,
) -> ChapterId:
    for chapter_id, chapter_package in chapter_packages.items():
        if any(paragraph.id == paragraph_id_value for paragraph in chapter_package.paragraphs):
            return chapter_id
    raise KeyError(f"paragraph {paragraph_id_value} not found in chapter packages")
