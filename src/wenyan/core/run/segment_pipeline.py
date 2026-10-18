from wenyan.core.ports.artifact_ref import SegmentArtifactKind, SegmentRef
from wenyan.core.ports.artifact_store import ArtifactStore
from wenyan_models.artifacts.segment import (
    ContextReviewArtifact,
    GlossReviewArtifact,
    GrammarReviewArtifact,
    TokenizationReviewArtifact,
)
from wenyan_models.domain.enums import ComponentKind, ReviewStatus, UnitStatus
from wenyan_models.domain.ids import DocumentId, SegmentId

type SegmentReviewArtifact = (
    TokenizationReviewArtifact
    | GlossReviewArtifact
    | GrammarReviewArtifact
    | ContextReviewArtifact
)

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

_DRAFT_KIND: dict[ComponentKind, SegmentArtifactKind] = {
    ComponentKind.TOKENIZE_SEGMENT: SegmentArtifactKind.TOKENIZATION,
    ComponentKind.GLOSS_SEGMENT: SegmentArtifactKind.GLOSSES,
    ComponentKind.ANNOTATE_SEGMENT_GRAMMAR: SegmentArtifactKind.GRAMMAR_NOTES,
    ComponentKind.ANNOTATE_SEGMENT_CONTEXT: SegmentArtifactKind.CONTEXT_NOTES,
}

_REVIEW_KIND: dict[ComponentKind, SegmentArtifactKind] = {
    ComponentKind.REVIEW_SEGMENT_TOKENIZATION: SegmentArtifactKind.TOKENIZATION_REVIEW,
    ComponentKind.REVIEW_SEGMENT_GLOSS: SegmentArtifactKind.GLOSS_REVIEW,
    ComponentKind.REVIEW_SEGMENT_GRAMMAR: SegmentArtifactKind.GRAMMAR_REVIEW,
    ComponentKind.REVIEW_SEGMENT_CONTEXT: SegmentArtifactKind.CONTEXT_REVIEW,
}

_REVIEW_MODEL: dict[ComponentKind, type[SegmentReviewArtifact]] = {
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
) -> SegmentRef | None:
    if component in _DRAFT_KIND:
        return SegmentRef(_DRAFT_KIND[component], document_id, segment_id)
    if component in _REVIEW_KIND:
        return SegmentRef(_REVIEW_KIND[component], document_id, segment_id)
    return None


def component_unit_status(
    artifacts: ArtifactStore,
    document_id: DocumentId,
    segment_id: SegmentId,
    component: ComponentKind,
) -> UnitStatus:
    if component in _DRAFT_KIND:
        ref = SegmentRef(_DRAFT_KIND[component], document_id, segment_id)
        return UnitStatus.COMPLETE if artifacts.exists(ref) else UnitStatus.PENDING
    if component in _REVIEW_KIND:
        draft_component = _DRAFT_FOR_REVIEW[component]
        if not artifacts.exists(SegmentRef(_DRAFT_KIND[draft_component], document_id, segment_id)):
            return UnitStatus.PENDING
        review_ref = SegmentRef(_REVIEW_KIND[component], document_id, segment_id)
        if not artifacts.exists(review_ref):
            return UnitStatus.PENDING
        review = artifacts.read(review_ref, _REVIEW_MODEL[component])
        if review.status == ReviewStatus.APPROVED:
            return UnitStatus.COMPLETE
        return UnitStatus.BLOCKED
    return UnitStatus.PENDING


def read_review_component(
    artifacts: ArtifactStore,
    document_id: DocumentId,
    segment_id: SegmentId,
    component: ComponentKind,
) -> SegmentReviewArtifact | None:
    if component not in _REVIEW_KIND:
        return None
    review_ref = SegmentRef(_REVIEW_KIND[component], document_id, segment_id)
    if not artifacts.exists(review_ref):
        return None
    return artifacts.read(review_ref, _REVIEW_MODEL[component])


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
    review_ref = SegmentRef(_REVIEW_KIND[review_component], document_id, segment_id)
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
