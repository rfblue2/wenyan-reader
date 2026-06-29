from wenyan.jobs.context import JobContext, JobOptions
from wenyan_models.artifacts.segment import ContextNotesArtifact
from wenyan_models.domain.ids import DocumentId
from wenyan_models.domain.results import JobFailure, JobOutcome
from wenyan_models.domain.targets import SegmentTarget

_DRAFT_SKILL = ".cursor/skills/drafting-context-notes/SKILL.md"


def run_annotate_segment_context(
    ctx: JobContext,
    document_id: DocumentId,
    target: SegmentTarget,
    options: JobOptions,
) -> JobOutcome[ContextNotesArtifact]:
    del ctx, document_id, target, options
    return JobFailure(
        code="not-implemented",
        message=f"Context drafting is skill-driven; see {_DRAFT_SKILL}",
    )
