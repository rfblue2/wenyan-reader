from pathlib import Path

from wenyan.core.ports.artifact_ref import (
    chapter_proposal_ref,
    normalized_document_ref,
)
from wenyan.core.ports.artifact_store import ArtifactStore
from wenyan.core.ports.status_reader import StatusReader
from wenyan_models.artifacts.normalized import NormalizedDocument
from wenyan_models.artifacts.structure import ChapterProposal
from wenyan_models.domain.enums import UnitStatus
from wenyan_models.domain.ids import ChapterId, DocumentId, ParagraphId, SegmentId
from wenyan_models.status.document import DocumentStatus


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
        chapters: list[dict[str, object]] = []
        if self._artifacts.exists(chapter_proposal_ref(document_id_value)):
            proposal = self._artifacts.read(chapter_proposal_ref(document_id_value), ChapterProposal)
            chapters = [
                {
                    "chapterId": str(chapter.id),
                    "title": chapter.title,
                    "status": UnitStatus.PENDING.value,
                }
                for chapter in proposal.chapters
            ]
        return DocumentStatus.model_validate(
            {
                "documentId": str(document_id_value),
                "title": normalized.title,
                "scope": {"type": "document"},
                "source": {
                    "status": "normalized",
                    "normalizedDocumentPath": str(normalized_ref.document_id),
                    "sourceHash": str(normalized.source_hash),
                    "normalizedHash": str(normalized.normalized_hash),
                },
                "counts": {"pending": len(chapters)},
                "chapters": chapters,
            },
        )

    def chapter_status(self, document_id_value: DocumentId, chapter_id: ChapterId) -> DocumentStatus:
        return self.document_status(document_id_value)

    def paragraph_status(
        self,
        document_id_value: DocumentId,
        paragraph_id: ParagraphId,
    ) -> DocumentStatus:
        return self.document_status(document_id_value)

    def segment_status(
        self,
        document_id_value: DocumentId,
        segment_id: SegmentId,
    ) -> DocumentStatus:
        return self.document_status(document_id_value)
