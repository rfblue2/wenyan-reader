from pathlib import Path

from wenyan.core.adapters.paths import artifact_path
from wenyan.core.ports.artifact_ref import chapter_proposal_ref, normalized_document_ref
from wenyan.core.ports.artifact_store import ArtifactStore
from wenyan.core.ports.status_reader import StatusReader
from wenyan.core.status.derivation import (
    derive_chapter_status,
    derive_document_status,
    derive_paragraph_status,
    derive_segment_status,
    find_paragraph_chapter,
    find_segment_location,
)
from wenyan_models.artifacts.normalized import NormalizedDocument
from wenyan_models.artifacts.structure import ChapterProposal
from wenyan_models.domain.ids import ChapterId, DocumentId, ParagraphId, SegmentId
from wenyan_models.status.chapter import ChapterStatus
from wenyan_models.status.document import DocumentSourceStatus, DocumentStatus
from wenyan_models.status.paragraph import ParagraphStatus
from wenyan_models.status.segment import SegmentStatus


class FilesystemStatusReader(StatusReader):
    def __init__(self, artifacts: ArtifactStore, repo_root: Path) -> None:
        self._artifacts = artifacts
        self._repo_root = repo_root

    def document_status(self, document_id_value: DocumentId) -> DocumentStatus:
        normalized_ref = normalized_document_ref(document_id_value)
        if not self._artifacts.exists(normalized_ref):
            return DocumentStatus.model_validate(
                {
                    "documentId": str(document_id_value),
                    "title": "",
                    "scope": {"type": "document"},
                    "source": {
                        "status": "pending",
                        "normalizedDocumentPath": "",
                        "sourceHash": "",
                        "normalizedHash": "",
                    },
                    "counts": {},
                },
            )
        normalized = self._artifacts.read(normalized_ref, NormalizedDocument)
        source = DocumentSourceStatus.model_validate(
            {
                "status": "normalized",
                "normalizedDocumentPath": str(
                    artifact_path(self._repo_root, normalized_ref).relative_to(self._repo_root),
                ),
                "sourceHash": str(normalized.source_hash),
                "normalizedHash": str(normalized.normalized_hash),
            },
        )
        chapter_items: list[tuple[str, ChapterId]] = []
        if self._artifacts.exists(chapter_proposal_ref(document_id_value)):
            proposal = self._artifacts.read(chapter_proposal_ref(document_id_value), ChapterProposal)
            chapter_items = [(chapter.title, chapter.id) for chapter in proposal.chapters]
        return derive_document_status(
            self._artifacts,
            self._repo_root,
            document_id=document_id_value,
            title=normalized.title,
            source=source,
            chapter_items=chapter_items,
        )

    def chapter_status(self, document_id_value: DocumentId, chapter_id: ChapterId) -> ChapterStatus:
        return derive_chapter_status(
            self._artifacts,
            self._repo_root,
            document_id=document_id_value,
            chapter_id=chapter_id,
        )

    def paragraph_status(
        self,
        document_id_value: DocumentId,
        paragraph_id_value: ParagraphId,
    ) -> ParagraphStatus:
        chapter_id_value = find_paragraph_chapter(self._artifacts, document_id_value, paragraph_id_value)
        if chapter_id_value is None:
            raise ValueError(f"paragraph {paragraph_id_value} was not found in document {document_id_value}")
        return derive_paragraph_status(
            self._artifacts,
            self._repo_root,
            document_id=document_id_value,
            chapter_id=chapter_id_value,
            paragraph_id=paragraph_id_value,
        )

    def segment_status(
        self,
        document_id_value: DocumentId,
        segment_id_value: SegmentId,
    ) -> SegmentStatus:
        location = find_segment_location(self._artifacts, document_id_value, segment_id_value)
        if location is None:
            raise ValueError(f"segment {segment_id_value} was not found in document {document_id_value}")
        chapter_id_value, paragraph_id_value, text = location
        return derive_segment_status(
            self._artifacts,
            self._repo_root,
            document_id=document_id_value,
            chapter_id=chapter_id_value,
            paragraph_id=paragraph_id_value,
            segment_id=segment_id_value,
            text=text,
        )
