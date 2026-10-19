from dataclasses import dataclass

from wenyan.core.assembly.state import AssemblyState, ParagraphAssembly, inspect_paragraph_assembly
from wenyan.core.ports.artifact_ref import ParagraphArtifactKind, ParagraphRef
from wenyan.core.ports.artifact_store import ArtifactStore
from wenyan.core.run.work_queue import iter_paragraphs
from wenyan_models.domain.ids import ChapterId, ContentHash, DocumentId, ParagraphId
from wenyan_models.reader.paragraph import ParagraphPackage


@dataclass(frozen=True)
class ReadyParagraph:
    chapter_id: ChapterId
    chapter_title: str
    paragraph_id: ParagraphId
    package: ParagraphPackage
    assembly_input_hash: ContentHash


def collect_ready_paragraphs(
    artifacts: ArtifactStore,
    document_id: DocumentId,
) -> tuple[ReadyParagraph, ...]:
    items: list[ReadyParagraph] = []
    for chapter, paragraph in iter_paragraphs(artifacts, document_id):
        match inspect_paragraph_assembly(artifacts, document_id, paragraph.id):
            case ParagraphAssembly(state=AssemblyState.CURRENT, input_hash=input_hash):
                package_ref = ParagraphRef(
                    ParagraphArtifactKind.ASSEMBLY_PACKAGE, document_id, paragraph.id
                )
                items.append(
                    ReadyParagraph(
                        chapter_id=chapter.id,
                        chapter_title=chapter.title,
                        paragraph_id=paragraph.id,
                        package=artifacts.read(package_ref, ParagraphPackage),
                        assembly_input_hash=input_hash,
                    ),
                )
    return tuple(items)
