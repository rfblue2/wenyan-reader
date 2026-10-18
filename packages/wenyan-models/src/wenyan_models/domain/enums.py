from enum import StrEnum


class ComponentKind(StrEnum):
    TOKENIZE_SEGMENT = "tokenize-segment"
    REVIEW_SEGMENT_TOKENIZATION = "review-segment-tokenization"
    GLOSS_SEGMENT = "gloss-segment"
    REVIEW_SEGMENT_GLOSS = "review-segment-gloss"
    ANNOTATE_SEGMENT_GRAMMAR = "annotate-segment-grammar"
    REVIEW_SEGMENT_GRAMMAR = "review-segment-grammar"
    ANNOTATE_SEGMENT_CONTEXT = "annotate-segment-context"
    REVIEW_SEGMENT_CONTEXT = "review-segment-context"
    ASSEMBLE_PARAGRAPH = "assemble-paragraph"


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
