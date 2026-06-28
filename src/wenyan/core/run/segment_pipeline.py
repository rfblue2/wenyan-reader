from collections.abc import Callable

from wenyan.core.ports.artifact_ref import (
    ArtifactRef,
    segment_context_notes_ref,
    segment_context_review_ref,
    segment_gloss_review_ref,
    segment_glosses_ref,
    segment_grammar_notes_ref,
    segment_grammar_review_ref,
    segment_tokenization_ref,
    segment_tokenization_review_ref,
)
from wenyan.core.ports.artifact_store import ArtifactStore
from wenyan_models.artifacts.segment import (
    GlossReviewArtifact,
    TokenizationReviewArtifact,
)
from wenyan_models.domain.enums import ComponentKind, ReviewStatus
from wenyan_models.domain.ids import DocumentId, SegmentId

SEGMENT_SUBJOBS: tuple[ComponentKind, ...] = (
    ComponentKind.TOKENIZE_SEGMENT,
    ComponentKind.REVIEW_SEGMENT_TOKENIZATION,
    ComponentKind.GLOSS_SEGMENT,
    ComponentKind.REVIEW_SEGMENT_GLOSS,
    ComponentKind.ANNOTATE_SEGMENT_GRAMMAR,
    ComponentKind.REVIEW_SEGMENT_GRAMMAR,
    ComponentKind.ANNOTATE_SEGMENT_CONTEXT,
    ComponentKind.REVIEW_SEGMENT_CONTEXT,
)

_DRAFT_REF: dict[ComponentKind, Callable[[DocumentId, SegmentId], ArtifactRef]] = {
    ComponentKind.TOKENIZE_SEGMENT: segment_tokenization_ref,
    ComponentKind.GLOSS_SEGMENT: segment_glosses_ref,
    ComponentKind.ANNOTATE_SEGMENT_GRAMMAR: segment_grammar_notes_ref,
    ComponentKind.ANNOTATE_SEGMENT_CONTEXT: segment_context_notes_ref,
}

_REVIEW_REF: dict[ComponentKind, Callable[[DocumentId, SegmentId], ArtifactRef]] = {
    ComponentKind.REVIEW_SEGMENT_TOKENIZATION: segment_tokenization_review_ref,
    ComponentKind.REVIEW_SEGMENT_GLOSS: segment_gloss_review_ref,
    ComponentKind.REVIEW_SEGMENT_GRAMMAR: segment_grammar_review_ref,
    ComponentKind.REVIEW_SEGMENT_CONTEXT: segment_context_review_ref,
}

_REVIEW_MODEL = {
    ComponentKind.REVIEW_SEGMENT_TOKENIZATION: TokenizationReviewArtifact,
    ComponentKind.REVIEW_SEGMENT_GLOSS: GlossReviewArtifact,
}


def segment_is_complete(
    artifacts: ArtifactStore,
    document_id: DocumentId,
    segment_id: SegmentId,
) -> bool:
    return not pending_segment_subjobs(artifacts, document_id, segment_id)


def pending_segment_subjobs(
    artifacts: ArtifactStore,
    document_id: DocumentId,
    segment_id: SegmentId,
) -> tuple[ComponentKind, ...]:
    pending: list[ComponentKind] = []
    for component in SEGMENT_SUBJOBS:
        if not _component_is_complete(artifacts, document_id, segment_id, component):
            pending.append(component)
    return tuple(pending)


def _component_is_complete(
    artifacts: ArtifactStore,
    document_id: DocumentId,
    segment_id: SegmentId,
    component: ComponentKind,
) -> bool:
    if component in _DRAFT_REF:
        return artifacts.exists(_DRAFT_REF[component](document_id, segment_id))
    if component in _REVIEW_REF:
        review_ref = _REVIEW_REF[component](document_id, segment_id)
        if not artifacts.exists(review_ref):
            return False
        review_model = _REVIEW_MODEL.get(component)
        if review_model is None:
            return False
        review = artifacts.read(review_ref, review_model)
        return review.status == ReviewStatus.APPROVED
    return False
