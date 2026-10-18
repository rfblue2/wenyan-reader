from __future__ import annotations

from wenyan.core.assembly.input_hash import assembly_input_hash, segment_output_hash
from wenyan.core.assembly.load_segment_outputs import (
    MissingSegmentOutputError,
    load_all_segment_outputs,
)
from wenyan.core.ports.artifact_ref import ArtifactRef, ParagraphArtifactKind, ParagraphRef
from wenyan.core.ports.artifact_store import ArtifactStore
from wenyan_models.artifacts.assembly import ParagraphAssemblyValidationArtifact
from wenyan_models.artifacts.paragraph import ParagraphDraft
from wenyan_models.domain.enums import ComponentKind, UnitStatus, ValidationStatus
from wenyan_models.domain.ids import DocumentId, ParagraphId
from wenyan_models.status.component import ComponentStatusItem


def derive_paragraph_assembly_status(
    artifacts: ArtifactStore,
    document_id: DocumentId,
    paragraph_id: ParagraphId,
    *,
    segments_complete: bool,
) -> ComponentStatusItem:
    kind = ComponentKind.ASSEMBLE_PARAGRAPH
    package_ref = ParagraphRef(ParagraphArtifactKind.ASSEMBLY_PACKAGE, document_id, paragraph_id)
    validation_ref = ParagraphRef(
        ParagraphArtifactKind.ASSEMBLY_VALIDATION,
        document_id,
        paragraph_id,
    )
    if not segments_complete:
        return _component_item(kind, UnitStatus.PENDING, artifacts, package_ref)
    current_hash = compute_assembly_input_hash(artifacts, document_id, paragraph_id)
    if current_hash is None:
        return _component_item(kind, UnitStatus.PENDING, artifacts, package_ref)
    if not artifacts.exists(package_ref) or not artifacts.exists(validation_ref):
        return _component_item(kind, UnitStatus.PENDING, artifacts, package_ref)
    validation = artifacts.read(validation_ref, ParagraphAssemblyValidationArtifact)
    if validation.input_hash != current_hash:
        return _component_item(kind, UnitStatus.STALE, artifacts, package_ref)
    if validation.status != ValidationStatus.PASSED:
        return _component_item(kind, UnitStatus.PENDING, artifacts, package_ref)
    return _component_item(kind, UnitStatus.COMPLETE, artifacts, package_ref)


def compute_assembly_input_hash(
    artifacts: ArtifactStore,
    document_id: DocumentId,
    paragraph_id: ParagraphId,
) -> str | None:
    draft_ref = ParagraphRef(ParagraphArtifactKind.DRAFT, document_id, paragraph_id)
    if not artifacts.exists(draft_ref):
        return None
    draft = artifacts.read(draft_ref, ParagraphDraft)
    try:
        outputs = load_all_segment_outputs(artifacts, document_id, draft)
    except MissingSegmentOutputError:
        return None
    segment_hashes = {str(output.segment_id): segment_output_hash(output) for output in outputs}
    return str(assembly_input_hash(draft, segment_hashes))


def _component_item(
    kind: ComponentKind,
    status: UnitStatus,
    artifacts: ArtifactStore,
    ref: ArtifactRef,
) -> ComponentStatusItem:
    artifact_path_value = (
        ref.relative_path.as_posix() if artifacts.exists(ref) else None
    )
    return ComponentStatusItem.model_validate(
        {
            "kind": kind.value,
            "status": status.value,
            "artifactPath": artifact_path_value,
        },
    )
