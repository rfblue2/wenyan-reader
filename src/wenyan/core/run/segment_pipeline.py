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
    ContextReviewArtifact,
    GlossReviewArtifact,
    GrammarReviewArtifact,
    TokenizationReviewArtifact,
)
from wenyan_models.domain.enums import ComponentKind, ReviewStatus, UnitStatus
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
    ComponentKind.REVIEW_SEGMENT_GRAMMAR: GrammarReviewArtifact,
    ComponentKind.REVIEW_SEGMENT_CONTEXT: ContextReviewArtifact,
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


def component_artifact_ref(
    document_id: DocumentId,
    segment_id: SegmentId,
    component: ComponentKind,
) -> ArtifactRef | None:
    if component in _DRAFT_REF:
        return _DRAFT_REF[component](document_id, segment_id)
    if component in _REVIEW_REF:
        return _REVIEW_REF[component](document_id, segment_id)
    return None


def component_unit_status(
    artifacts: ArtifactStore,
    document_id: DocumentId,
    segment_id: SegmentId,
    component: ComponentKind,
) -> UnitStatus:
    if component in _DRAFT_REF:
        ref = _DRAFT_REF[component](document_id, segment_id)
        return UnitStatus.COMPLETE if artifacts.exists(ref) else UnitStatus.PENDING
    if component in _REVIEW_REF:
        draft_component = _DRAFT_FOR_REVIEW[component]
        if not artifacts.exists(_DRAFT_REF[draft_component](document_id, segment_id)):
            return UnitStatus.PENDING
        review_ref = _REVIEW_REF[component](document_id, segment_id)
        if not artifacts.exists(review_ref):
            return UnitStatus.PENDING
        review_model = _REVIEW_MODEL.get(component)
        if review_model is None:
            return UnitStatus.PENDING
        review = artifacts.read(review_ref, review_model)
        if review.status == ReviewStatus.APPROVED:
            return UnitStatus.COMPLETE
        return UnitStatus.BLOCKED
    return UnitStatus.PENDING


def read_review_component(
    artifacts: ArtifactStore,
    document_id: DocumentId,
    segment_id: SegmentId,
    component: ComponentKind,
) -> TokenizationReviewArtifact | GlossReviewArtifact | GrammarReviewArtifact | ContextReviewArtifact | None:
    if component not in _REVIEW_REF:
        return None
    review_ref = _REVIEW_REF[component](document_id, segment_id)
    if not artifacts.exists(review_ref):
        return None
    review_model = _REVIEW_MODEL.get(component)
    if review_model is None:
        return None
    return artifacts.read(review_ref, review_model)


_DRAFT_FOR_REVIEW: dict[ComponentKind, ComponentKind] = {
    ComponentKind.REVIEW_SEGMENT_TOKENIZATION: ComponentKind.TOKENIZE_SEGMENT,
    ComponentKind.REVIEW_SEGMENT_GLOSS: ComponentKind.GLOSS_SEGMENT,
    ComponentKind.REVIEW_SEGMENT_GRAMMAR: ComponentKind.ANNOTATE_SEGMENT_GRAMMAR,
    ComponentKind.REVIEW_SEGMENT_CONTEXT: ComponentKind.ANNOTATE_SEGMENT_CONTEXT,
}

_REVIEW_FOR_DRAFT: dict[ComponentKind, ComponentKind] = {
    draft: review for review, draft in _DRAFT_FOR_REVIEW.items()
}


def invalidate_segment_review(
    artifacts: ArtifactStore,
    document_id: DocumentId,
    segment_id: SegmentId,
    draft_component: ComponentKind,
    *,
    dry_run: bool,
) -> None:
    review_component = _REVIEW_FOR_DRAFT.get(draft_component)
    if review_component is None:
        return
    review_ref = _REVIEW_REF[review_component](document_id, segment_id)
    if dry_run or not artifacts.exists(review_ref):
        return
    artifacts.delete(review_ref)


def _component_is_complete(
    artifacts: ArtifactStore,
    document_id: DocumentId,
    segment_id: SegmentId,
    component: ComponentKind,
) -> bool:
    return component_unit_status(artifacts, document_id, segment_id, component) == UnitStatus.COMPLETE
