from pathlib import Path

from wenyan.core.ports.artifact_ref import ArtifactRef
from wenyan_models.domain.enums import ArtifactKind


def document_root(repo_root: Path, document_id) -> Path:
    return repo_root / "preprocess" / "documents" / str(document_id)


def normalized_text_path(repo_root: Path, document_id) -> Path:
    return document_root(repo_root, document_id) / "normalized-text.txt"


def artifact_path(repo_root: Path, ref: ArtifactRef) -> Path:
    root = document_root(repo_root, ref.document_id)
    match ref.kind:
        case ArtifactKind.NORMALIZED_DOCUMENT:
            return root / "normalized-document.json"
        case ArtifactKind.CHAPTER_PROPOSAL:
            return root / "structure" / "chapter-proposal.json"
        case ArtifactKind.CHAPTER_PROPOSAL_VALIDATION:
            return root / "structure" / "chapter-proposal.validation.json"
        case ArtifactKind.CHAPTER_SUMMARY:
            chapter_id = _require(ref.chapter_id, ref.kind, "chapter_id")
            return root / "structure" / "chapters" / str(chapter_id) / "summary.json"
        case ArtifactKind.PARAGRAPH_PROPOSAL:
            chapter_id = _require(ref.chapter_id, ref.kind, "chapter_id")
            return root / "structure" / "chapters" / str(chapter_id) / "paragraph-proposal.json"
        case ArtifactKind.PARAGRAPH_PROPOSAL_VALIDATION:
            chapter_id = _require(ref.chapter_id, ref.kind, "chapter_id")
            return (
                root
                / "structure"
                / "chapters"
                / str(chapter_id)
                / "paragraph-proposal.validation.json"
            )
        case ArtifactKind.PARAGRAPH_DRAFT:
            paragraph_id = _require(ref.paragraph_id, ref.kind, "paragraph_id")
            return root / "jobs" / "paragraphs" / str(paragraph_id) / "draft.json"
        case ArtifactKind.PARAGRAPH_DRAFT_VALIDATION:
            paragraph_id = _require(ref.paragraph_id, ref.kind, "paragraph_id")
            return root / "jobs" / "paragraphs" / str(paragraph_id) / "validation.json"
        case ArtifactKind.PARAGRAPH_DRAFT_REVIEW:
            paragraph_id = _require(ref.paragraph_id, ref.kind, "paragraph_id")
            return root / "jobs" / "paragraphs" / str(paragraph_id) / "review.json"
        case ArtifactKind.SEGMENT_INPUT:
            segment_id = _require(ref.segment_id, ref.kind, "segment_id")
            return root / "jobs" / "segments" / str(segment_id) / "input.json"
        case ArtifactKind.TOKENIZATION:
            segment_id = _require(ref.segment_id, ref.kind, "segment_id")
            return root / "jobs" / "segments" / str(segment_id) / "tokenization.json"
        case ArtifactKind.TOKENIZATION_REVIEW:
            segment_id = _require(ref.segment_id, ref.kind, "segment_id")
            return root / "jobs" / "segments" / str(segment_id) / "tokenization-review.json"
        case ArtifactKind.GLOSSES:
            segment_id = _require(ref.segment_id, ref.kind, "segment_id")
            return root / "jobs" / "segments" / str(segment_id) / "glosses.json"
        case ArtifactKind.GLOSS_REVIEW:
            segment_id = _require(ref.segment_id, ref.kind, "segment_id")
            return root / "jobs" / "segments" / str(segment_id) / "gloss-review.json"
        case ArtifactKind.GRAMMAR_NOTES:
            segment_id = _require(ref.segment_id, ref.kind, "segment_id")
            return root / "jobs" / "segments" / str(segment_id) / "grammar-notes.json"
        case ArtifactKind.GRAMMAR_REVIEW:
            segment_id = _require(ref.segment_id, ref.kind, "segment_id")
            return root / "jobs" / "segments" / str(segment_id) / "grammar-review.json"
        case ArtifactKind.CONTEXT_NOTES:
            segment_id = _require(ref.segment_id, ref.kind, "segment_id")
            return root / "jobs" / "segments" / str(segment_id) / "context-notes.json"
        case ArtifactKind.CONTEXT_REVIEW:
            segment_id = _require(ref.segment_id, ref.kind, "segment_id")
            return root / "jobs" / "segments" / str(segment_id) / "context-review.json"
        case ArtifactKind.ENTITY_INDEX:
            return root / "indexes" / "entity-index.json"
        case ArtifactKind.TERM_INDEX:
            return root / "indexes" / "term-index.json"
        case ArtifactKind.GLOSSARY_DRAFT:
            return root / "indexes" / "glossary-draft.json"
        case ArtifactKind.PARAGRAPH_ASSEMBLY_VALIDATION:
            paragraph_id = _require(ref.paragraph_id, ref.kind, "paragraph_id")
            return root / "jobs" / "assembly" / str(paragraph_id) / "validation.json"
        case ArtifactKind.PARAGRAPH_ASSEMBLY_REVIEW:
            paragraph_id = _require(ref.paragraph_id, ref.kind, "paragraph_id")
            return root / "jobs" / "assembly" / str(paragraph_id) / "review.json"
        case ArtifactKind.PACKAGE_VALIDATION:
            return root / "jobs" / "package" / "validation.json"


def _require[T](value: T | None, kind: ArtifactKind, field: str) -> T:
    if value is None:
        raise ValueError(f"{kind.value} requires {field}")
    return value
