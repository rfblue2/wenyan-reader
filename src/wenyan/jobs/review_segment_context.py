from wenyan_models.artifacts.segment import ContextReviewArtifact
from wenyan_models.domain.ids import DocumentId
from wenyan_models.domain.results import JobFailure, JobOutcome
from wenyan_models.domain.targets import SegmentTarget

from wenyan.jobs.context import JobContext, JobOptions

_REVIEW_SKILL = ".opencode/skills/reviewing-context-notes/SKILL.md"


def run_review_segment_context(
    ctx: JobContext,
    document_id: DocumentId,
    target: SegmentTarget,
    options: JobOptions,
) -> JobOutcome[ContextReviewArtifact]:
    del ctx, document_id, target, options
    return JobFailure(
        code="not-implemented",
        message=f"Context review is skill-driven; see {_REVIEW_SKILL}",
    )
