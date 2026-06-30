from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict

from wenyan_models.domain.enums import ArtifactKind
from wenyan_models.domain.ids import (
    ChapterId,
    DocumentId,
    ParagraphId,
    SegmentId,
)

_DEFAULT_MODEL_CONFIG = ConfigDict(frozen=True, populate_by_name=True, extra="forbid")


class ArtifactRef(BaseModel):
    model_config = _DEFAULT_MODEL_CONFIG

    kind: ArtifactKind
    document_id: DocumentId
    chapter_id: ChapterId | None = None
    paragraph_id: ParagraphId | None = None
    segment_id: SegmentId | None = None


@dataclass(frozen=True)
class _Scope:
    chapter: bool = False
    paragraph: bool = False
    segment: bool = False


_DOCUMENT_ONLY = _Scope()
_CHAPTER_SCOPE = _Scope(chapter=True)
_PARAGRAPH_SCOPE = _Scope(paragraph=True)
_SEGMENT_SCOPE = _Scope(segment=True)

_SCOPES: dict[ArtifactKind, _Scope] = {
    ArtifactKind.NORMALIZED_DOCUMENT: _DOCUMENT_ONLY,
    ArtifactKind.CHAPTER_PROPOSAL: _DOCUMENT_ONLY,
    ArtifactKind.CHAPTER_PROPOSAL_VALIDATION: _DOCUMENT_ONLY,
    ArtifactKind.ENTITY_INDEX: _DOCUMENT_ONLY,
    ArtifactKind.TERM_INDEX: _DOCUMENT_ONLY,
    ArtifactKind.GLOSSARY_DRAFT: _DOCUMENT_ONLY,
    ArtifactKind.PACKAGE_VALIDATION: _DOCUMENT_ONLY,
    ArtifactKind.CHAPTER_SUMMARY: _CHAPTER_SCOPE,
    ArtifactKind.PARAGRAPH_PROPOSAL: _CHAPTER_SCOPE,
    ArtifactKind.PARAGRAPH_PROPOSAL_VALIDATION: _CHAPTER_SCOPE,
    ArtifactKind.PARAGRAPH_DRAFT: _PARAGRAPH_SCOPE,
    ArtifactKind.PARAGRAPH_DRAFT_VALIDATION: _PARAGRAPH_SCOPE,
    ArtifactKind.PARAGRAPH_DRAFT_REVIEW: _PARAGRAPH_SCOPE,
    ArtifactKind.PARAGRAPH_ASSEMBLY_PACKAGE: _PARAGRAPH_SCOPE,
    ArtifactKind.PARAGRAPH_ASSEMBLY_VALIDATION: _PARAGRAPH_SCOPE,
    ArtifactKind.SEGMENT_INPUT: _SEGMENT_SCOPE,
    ArtifactKind.TOKENIZATION: _SEGMENT_SCOPE,
    ArtifactKind.TOKENIZATION_REVIEW: _SEGMENT_SCOPE,
    ArtifactKind.GLOSSES: _SEGMENT_SCOPE,
    ArtifactKind.GLOSS_REVIEW: _SEGMENT_SCOPE,
    ArtifactKind.GRAMMAR_NOTES: _SEGMENT_SCOPE,
    ArtifactKind.GRAMMAR_REVIEW: _SEGMENT_SCOPE,
    ArtifactKind.CONTEXT_NOTES: _SEGMENT_SCOPE,
    ArtifactKind.CONTEXT_REVIEW: _SEGMENT_SCOPE,
}


def _make_ref(
    kind: ArtifactKind,
    *,
    document_id: DocumentId,
    chapter_id: ChapterId | None = None,
    paragraph_id: ParagraphId | None = None,
    segment_id: SegmentId | None = None,
) -> ArtifactRef:
    scope = _SCOPES[kind]
    if chapter_id is not None and not scope.chapter:
        raise ValueError(f"{kind.value} does not accept chapter_id")
    if paragraph_id is not None and not scope.paragraph:
        raise ValueError(f"{kind.value} does not accept paragraph_id")
    if segment_id is not None and not scope.segment:
        raise ValueError(f"{kind.value} does not accept segment_id")
    if scope.chapter and chapter_id is None:
        raise ValueError(f"{kind.value} requires chapter_id")
    if scope.paragraph and paragraph_id is None:
        raise ValueError(f"{kind.value} requires paragraph_id")
    if scope.segment and segment_id is None:
        raise ValueError(f"{kind.value} requires segment_id")
    return ArtifactRef(
        kind=kind,
        document_id=document_id,
        chapter_id=chapter_id,
        paragraph_id=paragraph_id,
        segment_id=segment_id,
    )


def normalized_document_ref(document_id: DocumentId) -> ArtifactRef:
    return _make_ref(ArtifactKind.NORMALIZED_DOCUMENT, document_id=document_id)


def chapter_proposal_ref(document_id: DocumentId) -> ArtifactRef:
    return _make_ref(ArtifactKind.CHAPTER_PROPOSAL, document_id=document_id)


def chapter_proposal_validation_ref(document_id: DocumentId) -> ArtifactRef:
    return _make_ref(ArtifactKind.CHAPTER_PROPOSAL_VALIDATION, document_id=document_id)


def chapter_summary_ref(document_id: DocumentId, chapter_id: ChapterId) -> ArtifactRef:
    return _make_ref(
        ArtifactKind.CHAPTER_SUMMARY,
        document_id=document_id,
        chapter_id=chapter_id,
    )


def paragraph_proposal_ref(document_id: DocumentId, chapter_id: ChapterId) -> ArtifactRef:
    return _make_ref(
        ArtifactKind.PARAGRAPH_PROPOSAL,
        document_id=document_id,
        chapter_id=chapter_id,
    )


def paragraph_proposal_validation_ref(
    document_id: DocumentId,
    chapter_id: ChapterId,
) -> ArtifactRef:
    return _make_ref(
        ArtifactKind.PARAGRAPH_PROPOSAL_VALIDATION,
        document_id=document_id,
        chapter_id=chapter_id,
    )


def paragraph_draft_ref(document_id: DocumentId, paragraph_id: ParagraphId) -> ArtifactRef:
    return _make_ref(
        ArtifactKind.PARAGRAPH_DRAFT,
        document_id=document_id,
        paragraph_id=paragraph_id,
    )


def paragraph_draft_validation_ref(
    document_id: DocumentId,
    paragraph_id: ParagraphId,
) -> ArtifactRef:
    return _make_ref(
        ArtifactKind.PARAGRAPH_DRAFT_VALIDATION,
        document_id=document_id,
        paragraph_id=paragraph_id,
    )


def paragraph_draft_review_ref(document_id: DocumentId, paragraph_id: ParagraphId) -> ArtifactRef:
    return _make_ref(
        ArtifactKind.PARAGRAPH_DRAFT_REVIEW,
        document_id=document_id,
        paragraph_id=paragraph_id,
    )


def segment_input_ref(document_id: DocumentId, segment_id: SegmentId) -> ArtifactRef:
    return _make_ref(
        ArtifactKind.SEGMENT_INPUT,
        document_id=document_id,
        segment_id=segment_id,
    )


def segment_tokenization_ref(document_id: DocumentId, segment_id: SegmentId) -> ArtifactRef:
    return _make_ref(
        ArtifactKind.TOKENIZATION,
        document_id=document_id,
        segment_id=segment_id,
    )


def segment_tokenization_review_ref(
    document_id: DocumentId,
    segment_id: SegmentId,
) -> ArtifactRef:
    return _make_ref(
        ArtifactKind.TOKENIZATION_REVIEW,
        document_id=document_id,
        segment_id=segment_id,
    )


def segment_glosses_ref(document_id: DocumentId, segment_id: SegmentId) -> ArtifactRef:
    return _make_ref(
        ArtifactKind.GLOSSES,
        document_id=document_id,
        segment_id=segment_id,
    )


def segment_gloss_review_ref(document_id: DocumentId, segment_id: SegmentId) -> ArtifactRef:
    return _make_ref(
        ArtifactKind.GLOSS_REVIEW,
        document_id=document_id,
        segment_id=segment_id,
    )


def segment_grammar_notes_ref(document_id: DocumentId, segment_id: SegmentId) -> ArtifactRef:
    return _make_ref(
        ArtifactKind.GRAMMAR_NOTES,
        document_id=document_id,
        segment_id=segment_id,
    )


def segment_grammar_review_ref(document_id: DocumentId, segment_id: SegmentId) -> ArtifactRef:
    return _make_ref(
        ArtifactKind.GRAMMAR_REVIEW,
        document_id=document_id,
        segment_id=segment_id,
    )


def segment_context_notes_ref(document_id: DocumentId, segment_id: SegmentId) -> ArtifactRef:
    return _make_ref(
        ArtifactKind.CONTEXT_NOTES,
        document_id=document_id,
        segment_id=segment_id,
    )


def segment_context_review_ref(document_id: DocumentId, segment_id: SegmentId) -> ArtifactRef:
    return _make_ref(
        ArtifactKind.CONTEXT_REVIEW,
        document_id=document_id,
        segment_id=segment_id,
    )


def entity_index_ref(document_id: DocumentId) -> ArtifactRef:
    return _make_ref(ArtifactKind.ENTITY_INDEX, document_id=document_id)


def term_index_ref(document_id: DocumentId) -> ArtifactRef:
    return _make_ref(ArtifactKind.TERM_INDEX, document_id=document_id)


def glossary_draft_ref(document_id: DocumentId) -> ArtifactRef:
    return _make_ref(ArtifactKind.GLOSSARY_DRAFT, document_id=document_id)


def paragraph_assembly_package_ref(
    document_id: DocumentId,
    paragraph_id: ParagraphId,
) -> ArtifactRef:
    return _make_ref(
        ArtifactKind.PARAGRAPH_ASSEMBLY_PACKAGE,
        document_id=document_id,
        paragraph_id=paragraph_id,
    )


def paragraph_assembly_validation_ref(
    document_id: DocumentId,
    paragraph_id: ParagraphId,
) -> ArtifactRef:
    return _make_ref(
        ArtifactKind.PARAGRAPH_ASSEMBLY_VALIDATION,
        document_id=document_id,
        paragraph_id=paragraph_id,
    )


def package_validation_ref(document_id: DocumentId) -> ArtifactRef:
    return _make_ref(ArtifactKind.PACKAGE_VALIDATION, document_id=document_id)
