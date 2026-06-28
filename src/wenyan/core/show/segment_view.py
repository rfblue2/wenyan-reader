from __future__ import annotations

from pathlib import Path

from wenyan.core.ports.artifact_ref import (
    segment_glosses_ref,
    segment_input_ref,
    segment_tokenization_ref,
)
from wenyan.core.ports.artifact_store import ArtifactStore
from wenyan.core.run.segment_pipeline import read_review_component
from wenyan.core.status.derivation import derive_segment_status, find_segment_location
from wenyan_models.artifacts.segment import (
    GlossEntry,
    GlossesArtifact,
    SegmentInput,
    TokenizationArtifact,
)
from wenyan_models.domain.enums import ComponentKind
from wenyan_models.domain.ids import DocumentId, SegmentId
from wenyan_models.show.segment import ReviewShowItem, SegmentShowView, TokenGlossRow

_REVIEW_COMPONENTS: tuple[ComponentKind, ...] = (
    ComponentKind.REVIEW_SEGMENT_TOKENIZATION,
    ComponentKind.REVIEW_SEGMENT_GLOSS,
    ComponentKind.REVIEW_SEGMENT_GRAMMAR,
    ComponentKind.REVIEW_SEGMENT_CONTEXT,
)


def build_segment_show_view(
    artifacts: ArtifactStore,
    repo_root: Path,
    *,
    document_id: DocumentId,
    document_ref: str,
    segment_id: SegmentId,
    chapter_handle: str | None = None,
    paragraph_handle: str | None = None,
    segment_handle: str | None = None,
) -> SegmentShowView:
    location = find_segment_location(artifacts, document_id, segment_id)
    if location is None:
        raise ValueError(f"segment {segment_id} was not found in document {document_id}")
    chapter_id_value, paragraph_id_value, text = location
    segment_status = derive_segment_status(
        artifacts,
        repo_root,
        document_id=document_id,
        chapter_id=chapter_id_value,
        paragraph_id=paragraph_id_value,
        segment_id=segment_id,
        text=text,
    )
    return SegmentShowView.model_validate(
        {
            "documentId": str(document_id),
            "documentRef": document_ref,
            "chapterId": str(chapter_id_value),
            "chapterHandle": chapter_handle,
            "paragraphId": str(paragraph_id_value),
            "paragraphHandle": paragraph_handle,
            "segmentId": str(segment_id),
            "segmentHandle": segment_handle,
            "text": text,
            "status": segment_status.status.value,
            "tokens": [
                token.model_dump(by_alias=True)
                for token in _build_token_rows(artifacts, document_id, segment_id)
            ],
            "reviews": [
                review.model_dump(by_alias=True)
                for review in _build_review_items(artifacts, document_id, segment_id)
            ],
            "components": [
                component.model_dump(by_alias=True) for component in segment_status.components
            ],
        },
    )


def _build_token_rows(
    artifacts: ArtifactStore,
    document_id: DocumentId,
    segment_id: SegmentId,
) -> tuple[TokenGlossRow, ...]:
    tokenization_ref = segment_tokenization_ref(document_id, segment_id)
    if not artifacts.exists(tokenization_ref):
        return ()
    tokenization = artifacts.read(tokenization_ref, TokenizationArtifact)
    glosses: GlossesArtifact | None = None
    glosses_ref = segment_glosses_ref(document_id, segment_id)
    if artifacts.exists(glosses_ref):
        glosses = artifacts.read(glosses_ref, GlossesArtifact)
    candidate_glosses: tuple[dict[str, object], ...] = ()
    input_ref = segment_input_ref(document_id, segment_id)
    if artifacts.exists(input_ref):
        segment_input = artifacts.read(input_ref, SegmentInput)
        candidate_glosses = segment_input.candidate_glosses
    decisions_by_token = (
        {decision.token_id: decision for decision in glosses.gloss_decisions}
        if glosses is not None
        else {}
    )
    rows: list[TokenGlossRow] = []
    for token in tokenization.tokens:
        decision = decisions_by_token.get(token.id)
        pinyin: str | None = None
        gloss: str | None = None
        decision_value = None
        if decision is not None and glosses is not None:
            decision_value = decision.decision
            entry = _resolve_gloss_entry(decision.gloss_id, glosses.new_glosses, candidate_glosses)
            if entry is not None:
                pinyin = entry.pinyin
                gloss = entry.gloss
        rows.append(
            TokenGlossRow.model_validate(
                {
                    "tokenId": token.id,
                    "surface": token.surface,
                    "pinyin": pinyin,
                    "gloss": gloss,
                    "decision": decision_value,
                },
            ),
        )
    return tuple(rows)


def _resolve_gloss_entry(
    gloss_id: str,
    new_glosses: tuple[GlossEntry, ...],
    candidate_glosses: tuple[dict[str, object], ...],
) -> GlossEntry | None:
    for entry in new_glosses:
        if entry.id == gloss_id:
            return entry
    for candidate in candidate_glosses:
        if candidate.get("id") == gloss_id:
            return GlossEntry.model_validate(candidate)
    return None


def _build_review_items(
    artifacts: ArtifactStore,
    document_id: DocumentId,
    segment_id: SegmentId,
) -> tuple[ReviewShowItem, ...]:
    items: list[ReviewShowItem] = []
    for component in _REVIEW_COMPONENTS:
        review = read_review_component(artifacts, document_id, segment_id, component)
        if review is None:
            continue
        items.append(
            ReviewShowItem.model_validate(
                {
                    "kind": component.value,
                    "status": review.status.value,
                    "findings": list(review.findings),
                },
            ),
        )
    return tuple(items)
