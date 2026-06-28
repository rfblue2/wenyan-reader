from enum import StrEnum


class ArtifactKind(StrEnum):
    NORMALIZED_DOCUMENT = "normalized-document"
    CHAPTER_PROPOSAL = "chapter-proposal"
    CHAPTER_PROPOSAL_VALIDATION = "chapter-proposal-validation"
    CHAPTER_SUMMARY = "chapter-summary"
    PARAGRAPH_PROPOSAL = "paragraph-proposal"
    PARAGRAPH_PROPOSAL_VALIDATION = "paragraph-proposal-validation"
    PARAGRAPH_DRAFT = "paragraph-draft"
    PARAGRAPH_DRAFT_VALIDATION = "paragraph-draft-validation"
    PARAGRAPH_DRAFT_REVIEW = "paragraph-draft-review"
    SEGMENT_INPUT = "segment-input"
    TOKENIZATION = "tokenization"
    TOKENIZATION_REVIEW = "tokenization-review"
    GLOSSES = "glosses"
    GLOSS_REVIEW = "gloss-review"
    GRAMMAR_NOTES = "grammar-notes"
    GRAMMAR_REVIEW = "grammar-review"
    CONTEXT_NOTES = "context-notes"
    CONTEXT_REVIEW = "context-review"
    ENTITY_INDEX = "entity-index"
    TERM_INDEX = "term-index"
    GLOSSARY_DRAFT = "glossary-draft"
    PARAGRAPH_ASSEMBLY_VALIDATION = "paragraph-assembly-validation"
    PARAGRAPH_ASSEMBLY_REVIEW = "paragraph-assembly-review"
    PACKAGE_VALIDATION = "package-validation"


class ComponentKind(StrEnum):
    TOKENIZE_SEGMENT = "tokenize-segment"
    REVIEW_SEGMENT_TOKENIZATION = "review-segment-tokenization"
    GLOSS_SEGMENT = "gloss-segment"
    REVIEW_SEGMENT_GLOSS = "review-segment-gloss"
    ANNOTATE_SEGMENT_GRAMMAR = "annotate-segment-grammar"
    REVIEW_SEGMENT_GRAMMAR = "review-segment-grammar"
    ANNOTATE_SEGMENT_CONTEXT = "annotate-segment-context"
    REVIEW_SEGMENT_CONTEXT = "review-segment-context"


class UnitStatus(StrEnum):
    PENDING = "pending"
    IN_PROGRESS = "in-progress"
    COMPLETE = "complete"
    STALE = "stale"
    BLOCKED = "blocked"
    FAILED = "failed"


class ValidationStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"


class ReviewStatus(StrEnum):
    APPROVED = "approved"
    REJECTED = "rejected"
