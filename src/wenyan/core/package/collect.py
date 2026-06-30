from dataclasses import dataclass

from wenyan.core.ports.artifact_ref import paragraph_assembly_package_ref
from wenyan.core.ports.artifact_store import ArtifactStore
from wenyan.core.run.work_queue import _iter_paragraphs
from wenyan_models.domain.ids import ChapterId, DocumentId, ParagraphId
from wenyan_models.reader.paragraph import ParagraphPackage

from wenyan.core.package.ready import paragraph_assembly_is_ready


@dataclass(frozen=True)
class ReadyParagraph:
    chapter_id: ChapterId
    chapter_title: str
    paragraph_id: ParagraphId
    package: ParagraphPackage
    assembly_input_hash: str


def collect_ready_paragraphs(
    artifacts: ArtifactStore,
    document_id: DocumentId,
) -> tuple[ReadyParagraph, ...]:
    from wenyan.core.ports.artifact_ref import paragraph_assembly_validation_ref
    from wenyan_models.artifacts.assembly import ParagraphAssemblyValidationArtifact

    from wenyan.core.status.assembly import _compute_assembly_input_hash

    items: list[ReadyParagraph] = []
    for chapter, paragraph in _iter_paragraphs(artifacts, document_id):
        if not paragraph_assembly_is_ready(artifacts, document_id, paragraph.id):
            continue
        package_ref = paragraph_assembly_package_ref(document_id, paragraph.id)
        package = artifacts.read(package_ref, ParagraphPackage)
        validation_ref = paragraph_assembly_validation_ref(document_id, paragraph.id)
        validation = artifacts.read(validation_ref, ParagraphAssemblyValidationArtifact)
        assembly_hash = _compute_assembly_input_hash(artifacts, document_id, paragraph.id)
        assert assembly_hash is not None
        assert validation.input_hash == assembly_hash
        items.append(
            ReadyParagraph(
                chapter_id=chapter.id,
                chapter_title=chapter.title,
                paragraph_id=paragraph.id,
                package=package,
                assembly_input_hash=str(validation.input_hash),
            ),
        )
    return tuple(items)
