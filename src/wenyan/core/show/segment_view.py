from __future__ import annotations

from pathlib import Path

from wenyan.core.gloss.glossary_draft import load_glossary_draft
from wenyan.core.ports.artifact_ref import (
    segment_context_notes_ref,
    segment_glosses_ref,
    segment_grammar_notes_ref,
    segment_input_ref,
    segment_tokenization_ref,
)
from wenyan.core.ports.artifact_store import ArtifactStore
from wenyan.core.review.findings import format_review_findings
from wenyan.core.run.segment_pipeline import read_review_component
from wenyan.core.status.derivation import derive_segment_status, find_segment_location
from wenyan_models.artifacts.segment import (
    ContextNotesArtifact,
    ContextReviewArtifact,
    GlossEntry,
    GlossesArtifact,
    GrammarNotesArtifact,
    NoteItem,
    SegmentInput,
    TokenizationArtifact,
)
from wenyan_models.domain.enums import ComponentKind
from wenyan_models.domain.ids import DocumentId, SegmentId
from wenyan_models.show.segment import NoteShowItem, ReviewShowItem, SegmentShowView, TokenGlossRow

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
    token_rows = _build_token_rows(artifacts, document_id, segment_id)
    tokenization = _load_tokenization(artifacts, document_id, segment_id)
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
            "tokens": [token.model_dump(by_alias=True) for token in token_rows],
            "grammarNotes": [
                note.model_dump(by_alias=True)
                for note in _build_note_show_items(
                    _load_grammar_notes(artifacts, document_id, segment_id),
                    tokenization,
                )
            ],
            "contextNotes": [
                note.model_dump(by_alias=True)
                for note in _build_note_show_items(
                    _load_context_notes(artifacts, document_id, segment_id),
                    tokenization,
                )
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
    glossary_draft = load_glossary_draft(artifacts, document_id)
    candidate_entries = list(glossary_draft.glosses)
    input_ref = segment_input_ref(document_id, segment_id)
    if artifacts.exists(input_ref):
        segment_input = artifacts.read(input_ref, SegmentInput)
        candidate_entries.extend(
            GlossEntry.model_validate(dict(item)) for item in segment_input.candidate_glosses
        )
    candidate_glosses = tuple(
        entry.model_dump(by_alias=True) for entry in _unique_gloss_entries(candidate_entries)
    )
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


def _load_tokenization(
    artifacts: ArtifactStore,
    document_id: DocumentId,
    segment_id: SegmentId,
) -> TokenizationArtifact | None:
    tokenization_ref = segment_tokenization_ref(document_id, segment_id)
    if not artifacts.exists(tokenization_ref):
        return None
    return artifacts.read(tokenization_ref, TokenizationArtifact)


def _load_grammar_notes(
    artifacts: ArtifactStore,
    document_id: DocumentId,
    segment_id: SegmentId,
) -> tuple[NoteItem, ...]:
    grammar_ref = segment_grammar_notes_ref(document_id, segment_id)
    if not artifacts.exists(grammar_ref):
        return ()
    grammar = artifacts.read(grammar_ref, GrammarNotesArtifact)
    return grammar.grammar_notes


def _load_context_notes(
    artifacts: ArtifactStore,
    document_id: DocumentId,
    segment_id: SegmentId,
) -> tuple[NoteItem, ...]:
    context_ref = segment_context_notes_ref(document_id, segment_id)
    if not artifacts.exists(context_ref):
        return ()
    context = artifacts.read(context_ref, ContextNotesArtifact)
    return context.context_notes


def _build_note_show_items(
    notes: tuple[NoteItem, ...],
    tokenization: TokenizationArtifact | None,
) -> tuple[NoteShowItem, ...]:
    surfaces_by_id = (
        {token.id: token.surface for token in tokenization.tokens} if tokenization is not None else {}
    )
    items: list[NoteShowItem] = []
    for note in notes:
        anchor_surfaces = tuple(
            surfaces_by_id.get(token_id, token_id) for token_id in note.anchor_token_ids
        )
        items.append(
            NoteShowItem.model_validate(
                {
                    "id": note.id,
                    "type": note.type,
                    "anchorTokenIds": note.anchor_token_ids,
                    "anchorSurfaces": anchor_surfaces,
                    "body": note.body,
                    "sources": [source.model_dump(by_alias=True) for source in note.sources],
                },
            ),
        )
    return tuple(items)


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


def _unique_gloss_entries(entries: list[GlossEntry]) -> tuple[GlossEntry, ...]:
    by_id: dict[str, GlossEntry] = {}
    for entry in entries:
        by_id[entry.id] = entry
    return tuple(by_id.values())


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
        review_payload: dict[str, object] = {
            "kind": component,
            "status": review.status,
            "findings": list(review.findings),
            "findingLines": list(format_review_findings(review.findings)),
        }
        if isinstance(review, ContextReviewArtifact):
            review_payload["sourceGrounding"] = [
                item.model_dump(by_alias=True) for item in review.source_grounding
            ]
        items.append(ReviewShowItem.model_validate(review_payload))
    return tuple(items)
