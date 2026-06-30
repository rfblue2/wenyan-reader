from __future__ import annotations

from pathlib import Path

from wenyan.core.adapters.hashing import sha256_text
from wenyan.core.adapters.paths import artifact_path
from wenyan.core.assembly.input_hash import assembly_input_hash, segment_output_hash
from wenyan.core.assembly.load_segment_outputs import (
    MissingSegmentOutputError,
    load_all_segment_outputs,
)
from wenyan.core.ports.artifact_ref import (
    paragraph_assembly_package_ref,
    paragraph_assembly_review_ref,
    paragraph_assembly_validation_ref,
    paragraph_draft_ref,
)
from wenyan.core.ports.artifact_store import ArtifactStore
from wenyan.core.review.findings import format_review_finding
from wenyan_models.artifacts.assembly import (
    ParagraphAssemblyReviewArtifact,
    ParagraphAssemblyValidationArtifact,
)
from wenyan_models.artifacts.paragraph import ParagraphDraft
from wenyan_models.domain.enums import ComponentKind, ReviewStatus, UnitStatus, ValidationStatus
from wenyan_models.domain.ids import DocumentId, ParagraphId
from wenyan_models.reader.paragraph import ParagraphPackage
from wenyan_models.status.component import ComponentStatusItem
from wenyan_models.status.paragraph import ParagraphAssemblyStatus


def derive_paragraph_assembly_status(
    artifacts: ArtifactStore,
    repo_root: Path,
    document_id: DocumentId,
    paragraph_id: ParagraphId,
    *,
    segments_complete: bool,
) -> ParagraphAssemblyStatus:
    assemble = _derive_assemble_status(
        artifacts,
        repo_root,
        document_id,
        paragraph_id,
        segments_complete=segments_complete,
    )
    review = _derive_review_status(
        artifacts,
        repo_root,
        document_id,
        paragraph_id,
        assemble_status=assemble.status,
    )
    return ParagraphAssemblyStatus(assemble=assemble, review=review)


def _derive_assemble_status(
    artifacts: ArtifactStore,
    repo_root: Path,
    document_id: DocumentId,
    paragraph_id: ParagraphId,
    *,
    segments_complete: bool,
) -> ComponentStatusItem:
    kind = ComponentKind.ASSEMBLE_PARAGRAPH
    package_ref = paragraph_assembly_package_ref(document_id, paragraph_id)
    validation_ref = paragraph_assembly_validation_ref(document_id, paragraph_id)
    if not segments_complete:
        return _component_item(kind, UnitStatus.PENDING, artifacts, repo_root, package_ref)
    current_hash = _compute_assembly_input_hash(artifacts, document_id, paragraph_id)
    if current_hash is None:
        return _component_item(kind, UnitStatus.PENDING, artifacts, repo_root, package_ref)
    if not artifacts.exists(package_ref) or not artifacts.exists(validation_ref):
        return _component_item(kind, UnitStatus.PENDING, artifacts, repo_root, package_ref)
    validation = artifacts.read(validation_ref, ParagraphAssemblyValidationArtifact)
    if validation.input_hash != current_hash:
        return _component_item(kind, UnitStatus.STALE, artifacts, repo_root, package_ref)
    if validation.status != ValidationStatus.PASSED:
        return _component_item(kind, UnitStatus.PENDING, artifacts, repo_root, package_ref)
    return _component_item(kind, UnitStatus.COMPLETE, artifacts, repo_root, package_ref)


def _derive_review_status(
    artifacts: ArtifactStore,
    repo_root: Path,
    document_id: DocumentId,
    paragraph_id: ParagraphId,
    *,
    assemble_status: UnitStatus,
) -> ComponentStatusItem:
    kind = ComponentKind.REVIEW_PARAGRAPH_ASSEMBLY
    review_ref = paragraph_assembly_review_ref(document_id, paragraph_id)
    package_ref = paragraph_assembly_package_ref(document_id, paragraph_id)
    if assemble_status != UnitStatus.COMPLETE:
        return _component_item(kind, UnitStatus.PENDING, artifacts, repo_root, review_ref)
    if not artifacts.exists(package_ref):
        return _component_item(kind, UnitStatus.PENDING, artifacts, repo_root, review_ref)
    package = artifacts.read(package_ref, ParagraphPackage)
    package_hash = str(sha256_text(package.model_dump_json(by_alias=True)))
    if not artifacts.exists(review_ref):
        return _component_item(kind, UnitStatus.PENDING, artifacts, repo_root, review_ref)
    review = artifacts.read(review_ref, ParagraphAssemblyReviewArtifact)
    if review.status == ReviewStatus.REJECTED:
        return _component_item(
            kind,
            UnitStatus.BLOCKED,
            artifacts,
            repo_root,
            review_ref,
            attempts=review.attempts,
            blocked_reason=_blocked_reason(review.findings),
            required_fixes=review.findings,
        )
    if review.status == ReviewStatus.APPROVED and review.input_hash == package_hash:
        return _component_item(
            kind,
            UnitStatus.COMPLETE,
            artifacts,
            repo_root,
            review_ref,
            attempts=review.attempts,
        )
    return _component_item(
        kind,
        UnitStatus.PENDING,
        artifacts,
        repo_root,
        review_ref,
        attempts=review.attempts,
    )


def _compute_assembly_input_hash(
    artifacts: ArtifactStore,
    document_id: DocumentId,
    paragraph_id: ParagraphId,
) -> str | None:
    draft_ref = paragraph_draft_ref(document_id, paragraph_id)
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
    repo_root: Path,
    ref,
    *,
    attempts: int | None = None,
    blocked_reason: str | None = None,
    required_fixes: tuple[dict[str, object], ...] = (),
) -> ComponentStatusItem:
    artifact_path_value = (
        artifact_path(repo_root, ref).relative_to(repo_root).as_posix() if artifacts.exists(ref) else None
    )
    payload: dict[str, object] = {
        "kind": kind.value,
        "status": status.value,
        "artifactPath": artifact_path_value,
    }
    if attempts is not None:
        payload["attempts"] = attempts
    if blocked_reason is not None:
        payload["blockedReason"] = blocked_reason
    if required_fixes:
        payload["requiredFixes"] = list(required_fixes)
    return ComponentStatusItem.model_validate(payload)


def _blocked_reason(findings: tuple[dict[str, object], ...]) -> str | None:
    for finding in findings:
        line = format_review_finding(finding)
        if line:
            return line
    return None
