from dataclasses import dataclass

from wenyan.core.ports.artifact_ref import SegmentArtifactKind, SegmentRef
from wenyan.core.ports.artifact_store import ArtifactStore
from wenyan_models.artifacts.segment import ContextReviewArtifact, SegmentReview
from wenyan_models.domain.enums import ComponentKind, ReviewStatus, UnitStatus
from wenyan_models.domain.ids import DocumentId, SegmentId


@dataclass(frozen=True)
class SegmentStage:
    draft: ComponentKind
    review: ComponentKind
    draft_kind: SegmentArtifactKind
    review_kind: SegmentArtifactKind
    review_model: type[SegmentReview]


TOKENIZATION_STAGE = SegmentStage(
    ComponentKind.TOKENIZE_SEGMENT,
    ComponentKind.REVIEW_SEGMENT_TOKENIZATION,
    SegmentArtifactKind.TOKENIZATION,
    SegmentArtifactKind.TOKENIZATION_REVIEW,
    SegmentReview,
)
GLOSS_STAGE = SegmentStage(
    ComponentKind.GLOSS_SEGMENT,
    ComponentKind.REVIEW_SEGMENT_GLOSS,
    SegmentArtifactKind.GLOSSES,
    SegmentArtifactKind.GLOSS_REVIEW,
    SegmentReview,
)
GRAMMAR_STAGE = SegmentStage(
    ComponentKind.ANNOTATE_SEGMENT_GRAMMAR,
    ComponentKind.REVIEW_SEGMENT_GRAMMAR,
    SegmentArtifactKind.GRAMMAR_NOTES,
    SegmentArtifactKind.GRAMMAR_REVIEW,
    SegmentReview,
)
CONTEXT_STAGE = SegmentStage(
    ComponentKind.ANNOTATE_SEGMENT_CONTEXT,
    ComponentKind.REVIEW_SEGMENT_CONTEXT,
    SegmentArtifactKind.CONTEXT_NOTES,
    SegmentArtifactKind.CONTEXT_REVIEW,
    ContextReviewArtifact,
)
SEGMENT_STAGES = (TOKENIZATION_STAGE, GLOSS_STAGE, GRAMMAR_STAGE, CONTEXT_STAGE)

SEGMENT_SUBJOBS: tuple[ComponentKind, ...] = tuple(
    component for stage in SEGMENT_STAGES for component in (stage.draft, stage.review)
)

_BY_DRAFT = {stage.draft: stage for stage in SEGMENT_STAGES}
_BY_REVIEW = {stage.review: stage for stage in SEGMENT_STAGES}


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
    return tuple(
        component
        for component in SEGMENT_SUBJOBS
        if component_unit_status(artifacts, document_id, segment_id, component)
        != UnitStatus.COMPLETE
    )


def component_artifact_ref(
    document_id: DocumentId,
    segment_id: SegmentId,
    component: ComponentKind,
) -> SegmentRef | None:
    if stage := _BY_DRAFT.get(component):
        return SegmentRef(stage.draft_kind, document_id, segment_id)
    if stage := _BY_REVIEW.get(component):
        return SegmentRef(stage.review_kind, document_id, segment_id)
    return None


def component_unit_status(
    artifacts: ArtifactStore,
    document_id: DocumentId,
    segment_id: SegmentId,
    component: ComponentKind,
) -> UnitStatus:
    if stage := _BY_DRAFT.get(component):
        draft_ref = SegmentRef(stage.draft_kind, document_id, segment_id)
        return UnitStatus.COMPLETE if artifacts.exists(draft_ref) else UnitStatus.PENDING
    if stage := _BY_REVIEW.get(component):
        if not artifacts.exists(SegmentRef(stage.draft_kind, document_id, segment_id)):
            return UnitStatus.PENDING
        review = read_review_component(artifacts, document_id, segment_id, component)
        if review is None:
            return UnitStatus.PENDING
        if review.status == ReviewStatus.APPROVED:
            return UnitStatus.COMPLETE
        return UnitStatus.BLOCKED
    return UnitStatus.PENDING


def read_review_component(
    artifacts: ArtifactStore,
    document_id: DocumentId,
    segment_id: SegmentId,
    component: ComponentKind,
) -> SegmentReview | None:
    stage = _BY_REVIEW.get(component)
    if stage is None:
        return None
    review_ref = SegmentRef(stage.review_kind, document_id, segment_id)
    if not artifacts.exists(review_ref):
        return None
    return artifacts.read(review_ref, stage.review_model)

