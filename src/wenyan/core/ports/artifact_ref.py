from dataclasses import dataclass
from enum import StrEnum
from pathlib import PurePosixPath

from wenyan_models.domain.ids import (
    ChapterId,
    DocumentId,
    ParagraphId,
    SegmentId,
)

_DOCUMENTS = PurePosixPath("preprocess/documents")


class DocumentArtifactKind(StrEnum):
    NORMALIZED_DOCUMENT = "normalized-document"
    CHAPTER_PROPOSAL = "chapter-proposal"
    CHAPTER_PROPOSAL_VALIDATION = "chapter-proposal-validation"
    GLOSSARY_DRAFT = "glossary-draft"
    PACKAGE_VALIDATION = "package-validation"


class ChapterArtifactKind(StrEnum):
    PARAGRAPH_PROPOSAL = "paragraph-proposal"
    PARAGRAPH_PROPOSAL_VALIDATION = "paragraph-proposal-validation"


class ParagraphArtifactKind(StrEnum):
    DRAFT = "paragraph-draft"
    DRAFT_VALIDATION = "paragraph-draft-validation"
    ASSEMBLY_PACKAGE = "paragraph-assembly-package"
    ASSEMBLY_VALIDATION = "paragraph-assembly-validation"


class SegmentArtifactKind(StrEnum):
    INPUT = "segment-input"
    TOKENIZATION = "tokenization"
    TOKENIZATION_REVIEW = "tokenization-review"
    GLOSSES = "glosses"
    GLOSS_REVIEW = "gloss-review"
    GRAMMAR_NOTES = "grammar-notes"
    GRAMMAR_REVIEW = "grammar-review"
    CONTEXT_NOTES = "context-notes"
    CONTEXT_REVIEW = "context-review"


_DOCUMENT_FILES: dict[DocumentArtifactKind, str] = {
    DocumentArtifactKind.NORMALIZED_DOCUMENT: "normalized-document.json",
    DocumentArtifactKind.CHAPTER_PROPOSAL: "structure/chapter-proposal.json",
    DocumentArtifactKind.CHAPTER_PROPOSAL_VALIDATION: "structure/chapter-proposal.validation.json",
    DocumentArtifactKind.GLOSSARY_DRAFT: "indexes/glossary-draft.json",
    DocumentArtifactKind.PACKAGE_VALIDATION: "jobs/package/validation.json",
}

_CHAPTER_FILES: dict[ChapterArtifactKind, str] = {
    ChapterArtifactKind.PARAGRAPH_PROPOSAL: "paragraph-proposal.json",
    ChapterArtifactKind.PARAGRAPH_PROPOSAL_VALIDATION: "paragraph-proposal.validation.json",
}

# (directory under jobs/, filename): drafts and assembly outputs live in separate trees.
_PARAGRAPH_FILES: dict[ParagraphArtifactKind, tuple[str, str]] = {
    ParagraphArtifactKind.DRAFT: ("paragraphs", "draft.json"),
    ParagraphArtifactKind.DRAFT_VALIDATION: ("paragraphs", "validation.json"),
    ParagraphArtifactKind.ASSEMBLY_PACKAGE: ("assembly", "package.json"),
    ParagraphArtifactKind.ASSEMBLY_VALIDATION: ("assembly", "validation.json"),
}

_SEGMENT_FILES: dict[SegmentArtifactKind, str] = {
    SegmentArtifactKind.INPUT: "input.json",
    SegmentArtifactKind.TOKENIZATION: "tokenization.json",
    SegmentArtifactKind.TOKENIZATION_REVIEW: "tokenization-review.json",
    SegmentArtifactKind.GLOSSES: "glosses.json",
    SegmentArtifactKind.GLOSS_REVIEW: "gloss-review.json",
    SegmentArtifactKind.GRAMMAR_NOTES: "grammar-notes.json",
    SegmentArtifactKind.GRAMMAR_REVIEW: "grammar-review.json",
    SegmentArtifactKind.CONTEXT_NOTES: "context-notes.json",
    SegmentArtifactKind.CONTEXT_REVIEW: "context-review.json",
}


@dataclass(frozen=True)
class DocumentRef:
    kind: DocumentArtifactKind
    document_id: DocumentId

    @property
    def relative_path(self) -> PurePosixPath:
        return _DOCUMENTS / self.document_id / _DOCUMENT_FILES[self.kind]


@dataclass(frozen=True)
class ChapterRef:
    kind: ChapterArtifactKind
    document_id: DocumentId
    chapter_id: ChapterId

    @property
    def relative_path(self) -> PurePosixPath:
        chapter_dir = _DOCUMENTS / self.document_id / "structure" / "chapters" / self.chapter_id
        return chapter_dir / _CHAPTER_FILES[self.kind]


@dataclass(frozen=True)
class ParagraphRef:
    kind: ParagraphArtifactKind
    document_id: DocumentId
    paragraph_id: ParagraphId

    @property
    def relative_path(self) -> PurePosixPath:
        directory, filename = _PARAGRAPH_FILES[self.kind]
        return _DOCUMENTS / self.document_id / "jobs" / directory / self.paragraph_id / filename


@dataclass(frozen=True)
class SegmentRef:
    kind: SegmentArtifactKind
    document_id: DocumentId
    segment_id: SegmentId

    @property
    def relative_path(self) -> PurePosixPath:
        segment_dir = _DOCUMENTS / self.document_id / "jobs" / "segments" / self.segment_id
        return segment_dir / _SEGMENT_FILES[self.kind]


type ArtifactRef = DocumentRef | ChapterRef | ParagraphRef | SegmentRef
