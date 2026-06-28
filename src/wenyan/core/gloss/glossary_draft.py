from wenyan.core.ports.artifact_ref import (
    glossary_draft_ref,
    segment_gloss_review_ref,
    segment_glosses_ref,
)
from wenyan.core.ports.artifact_store import ArtifactStore
from wenyan.core.run.work_queue import iter_segments_in_document_order
from wenyan_models.artifacts.glossary import GlossaryDraft
from wenyan_models.artifacts.segment import (
    GlossEntry,
    GlossesArtifact,
    GlossReviewArtifact,
    TokenizationArtifact,
)
from wenyan_models.domain.enums import ReviewStatus
from wenyan_models.domain.ids import DocumentId, SegmentId


def load_glossary_draft(artifacts: ArtifactStore, document_id: DocumentId) -> GlossaryDraft:
    ref = glossary_draft_ref(document_id)
    if artifacts.exists(ref):
        return artifacts.read(ref, GlossaryDraft)
    return GlossaryDraft()


def save_glossary_draft(
    artifacts: ArtifactStore,
    document_id: DocumentId,
    draft: GlossaryDraft,
    *,
    dry_run: bool,
) -> None:
    artifacts.write(glossary_draft_ref(document_id), draft, dry_run=dry_run)


def load_candidate_glosses(
    artifacts: ArtifactStore,
    document_id: DocumentId,
    segment_id_value: SegmentId,
) -> tuple[GlossEntry, ...]:
    by_id: dict[str, GlossEntry] = {}
    for entry in load_glossary_draft(artifacts, document_id).glosses:
        by_id[entry.id] = entry
    for prior_segment_id in iter_segments_in_document_order(artifacts, document_id):
        if prior_segment_id == segment_id_value:
            break
        if not _gloss_review_is_approved(artifacts, document_id, prior_segment_id):
            continue
        glosses = artifacts.read(
            segment_glosses_ref(document_id, prior_segment_id),
            GlossesArtifact,
        )
        for entry in glosses.new_glosses:
            by_id[entry.id] = entry
    return tuple(by_id.values())


def merge_approved_glosses(draft: GlossaryDraft, glosses: GlossesArtifact) -> GlossaryDraft:
    by_id = {entry.id: entry for entry in draft.glosses}
    for entry in glosses.new_glosses:
        by_id.setdefault(entry.id, entry)
    return GlossaryDraft(glosses=tuple(by_id.values()))


def normalize_gloss_reuse(
    glosses: GlossesArtifact,
    tokenization: TokenizationArtifact,
    candidates: tuple[GlossEntry, ...],
) -> GlossesArtifact:
    token_by_id = {token.id: token for token in tokenization.tokens}
    candidate_by_id = {entry.id: entry for entry in candidates}
    candidate_by_key = {
        _gloss_key(entry.surface, entry.pinyin, entry.gloss): entry.id for entry in candidates
    }
    new_gloss_by_id = {entry.id: entry for entry in glosses.new_glosses}
    removed_new_ids: set[str] = set()
    updated_decisions = []
    for decision in glosses.gloss_decisions:
        if decision.gloss_id in candidate_by_id:
            updated_decisions.append(
                decision.model_copy(update={"decision": "reuse-existing"}),
            )
            if decision.decision == "create-new":
                removed_new_ids.add(decision.gloss_id)
            continue
        if decision.decision != "create-new":
            updated_decisions.append(decision)
            continue
        new_entry = new_gloss_by_id.get(decision.gloss_id)
        if new_entry is None:
            updated_decisions.append(decision)
            continue
        token = token_by_id.get(decision.token_id)
        surface = token.surface if token is not None else new_entry.surface
        key = _gloss_key(surface, new_entry.pinyin, new_entry.gloss)
        existing_id = candidate_by_key.get(key)
        if existing_id is not None:
            updated_decisions.append(
                decision.model_copy(
                    update={"gloss_id": existing_id, "decision": "reuse-existing"},
                ),
            )
            removed_new_ids.add(decision.gloss_id)
            continue
        updated_decisions.append(decision)
        candidate_by_key[key] = decision.gloss_id
        candidate_by_id[decision.gloss_id] = new_entry
    new_glosses = tuple(
        entry for entry in glosses.new_glosses if entry.id not in removed_new_ids
    )
    new_gloss_ids = tuple(
        gloss_id for gloss_id in glosses.new_gloss_ids if gloss_id not in removed_new_ids
    )
    return glosses.model_copy(
        update={
            "gloss_decisions": tuple(updated_decisions),
            "new_glosses": new_glosses,
            "new_gloss_ids": new_gloss_ids,
        },
    )


def _gloss_review_is_approved(
    artifacts: ArtifactStore,
    document_id: DocumentId,
    segment_id_value: SegmentId,
) -> bool:
    review_ref = segment_gloss_review_ref(document_id, segment_id_value)
    if not artifacts.exists(review_ref):
        return False
    review = artifacts.read(review_ref, GlossReviewArtifact)
    return review.status == ReviewStatus.APPROVED


def _gloss_key(surface: str, pinyin: str, gloss: str) -> tuple[str, str, str]:
    return (
        surface,
        pinyin.strip().lower(),
        " ".join(gloss.strip().lower().split()),
    )
