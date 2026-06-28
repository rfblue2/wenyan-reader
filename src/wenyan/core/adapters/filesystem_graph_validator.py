from pathlib import Path

from wenyan.core.adapters.filesystem_normalized_text_store import FilesystemNormalizedTextStore
from wenyan.core.ports.artifact_ref import normalized_document_ref
from wenyan.core.ports.artifact_store import ArtifactStore
from wenyan.core.ports.graph_validator import GraphValidationReport, GraphValidator, ValidationIssue
from wenyan_models.artifacts.normalized import NormalizedDocument
from wenyan_models.domain.ids import ChapterId, DocumentId, ParagraphId, SegmentId


class FilesystemGraphValidator(GraphValidator):
    def __init__(self, artifacts: ArtifactStore, repo_root: Path) -> None:
        self._artifacts = artifacts
        self._normalized_text = FilesystemNormalizedTextStore(repo_root, artifacts)

    def validate_document(self, document_id: DocumentId) -> GraphValidationReport:
        issues: list[ValidationIssue] = []
        ref = normalized_document_ref(document_id)
        if not self._artifacts.exists(ref):
            issues.append(
                ValidationIssue(
                    code="missing-artifact",
                    message="normalized document is missing",
                    ref=ref,
                ),
            )
            return GraphValidationReport(issues=tuple(issues))
        normalized = self._artifacts.read(ref, NormalizedDocument)
        if not self._normalized_text.sidecar_exists(document_id):
            issues.append(
                ValidationIssue(
                    code="missing-artifact",
                    message="normalized text sidecar is missing",
                    ref=ref,
                ),
            )
            return GraphValidationReport(issues=tuple(issues))
        if not self._normalized_text.verify_hash(document_id, normalized.normalized_hash):
            issues.append(
                ValidationIssue(
                    code="hash-mismatch",
                    message="normalized text hash does not match manifest",
                    ref=ref,
                ),
            )
        return GraphValidationReport(issues=tuple(issues))

    def validate_chapter(
        self,
        document_id: DocumentId,
        chapter_id: ChapterId,
    ) -> GraphValidationReport:
        return self.validate_document(document_id)

    def validate_paragraph(
        self,
        document_id: DocumentId,
        paragraph_id: ParagraphId,
    ) -> GraphValidationReport:
        return self.validate_document(document_id)

    def validate_segment(
        self,
        document_id: DocumentId,
        segment_id: SegmentId,
    ) -> GraphValidationReport:
        return self.validate_document(document_id)
