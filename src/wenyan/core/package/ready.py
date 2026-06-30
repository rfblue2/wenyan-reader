from wenyan.core.ports.artifact_ref import (
    paragraph_assembly_package_ref,
    paragraph_assembly_validation_ref,
    paragraph_draft_ref,
)
from wenyan.core.ports.artifact_store import ArtifactStore
from wenyan.core.run.segment_pipeline import segment_is_complete
from wenyan_models.artifacts.assembly import ParagraphAssemblyValidationArtifact
from wenyan_models.artifacts.paragraph import ParagraphDraft
from wenyan_models.domain.enums import ValidationStatus
from wenyan_models.domain.ids import DocumentId, ParagraphId

from wenyan.core.status.assembly import _compute_assembly_input_hash


def paragraph_segments_complete(
    artifacts: ArtifactStore,
    document_id: DocumentId,
    paragraph_id: ParagraphId,
) -> bool:
    draft_ref = paragraph_draft_ref(document_id, paragraph_id)
    if not artifacts.exists(draft_ref):
        return False
    draft = artifacts.read(draft_ref, ParagraphDraft)
    return all(segment_is_complete(artifacts, document_id, segment.id) for segment in draft.segments)


def paragraph_assembly_is_ready(
    artifacts: ArtifactStore,
    document_id: DocumentId,
    paragraph_id: ParagraphId,
) -> bool:
    if not paragraph_segments_complete(artifacts, document_id, paragraph_id):
        return False
    package_ref = paragraph_assembly_package_ref(document_id, paragraph_id)
    validation_ref = paragraph_assembly_validation_ref(document_id, paragraph_id)
    if not artifacts.exists(package_ref) or not artifacts.exists(validation_ref):
        return False
    current_hash = _compute_assembly_input_hash(artifacts, document_id, paragraph_id)
    if current_hash is None:
        return False
    validation = artifacts.read(validation_ref, ParagraphAssemblyValidationArtifact)
    return validation.input_hash == current_hash and validation.status == ValidationStatus.PASSED
