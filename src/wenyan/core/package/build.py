from collections import OrderedDict

from wenyan_models.domain.ids import ChapterId, DocumentId, ParagraphId
from wenyan_models.reader.document import (
    ChapterNavItem,
    ChapterPackage,
    DocumentManifest,
    ParagraphNavItem,
)

from wenyan.core.package.collect import ReadyParagraph


def _chapter_manifest_path(chapter_id: ChapterId) -> str:
    return f"chapters/{chapter_id}/chapter.json"


def _paragraph_path(paragraph_id: ParagraphId) -> str:
    return f"paragraphs/{paragraph_id}.json"


def build_document_package(
    document_id: DocumentId,
    title: str,
    ready_paragraphs: tuple[ReadyParagraph, ...],
) -> tuple[DocumentManifest, dict[ChapterId, ChapterPackage], dict[ParagraphId, ReadyParagraph]]:
    chapters: OrderedDict[ChapterId, list[ReadyParagraph]] = OrderedDict()
    for item in ready_paragraphs:
        chapters.setdefault(item.chapter_id, []).append(item)

    chapter_nav: list[ChapterNavItem] = []
    chapter_packages: dict[ChapterId, ChapterPackage] = {}
    paragraph_index: dict[ParagraphId, ReadyParagraph] = {}

    for chapter_id, paragraph_items in chapters.items():
        chapter_title = paragraph_items[0].chapter_title
        paragraph_nav = tuple(
            ParagraphNavItem(id=item.paragraph_id, path=_paragraph_path(item.paragraph_id))
            for item in paragraph_items
        )
        chapter_packages[chapter_id] = ChapterPackage(
            id=chapter_id,
            title=chapter_title,
            paragraphs=paragraph_nav,
        )
        chapter_nav.append(
            ChapterNavItem(
                id=chapter_id,
                title=chapter_title,
                path=_chapter_manifest_path(chapter_id),
            ),
        )
        for item in paragraph_items:
            paragraph_index[item.paragraph_id] = item

    manifest = DocumentManifest(
        id=document_id,
        title=title,
        chapters=tuple(chapter_nav),
    )
    return manifest, chapter_packages, paragraph_index
