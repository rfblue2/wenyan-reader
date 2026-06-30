from wenyan.core.run.orphan_segments import PruneOrphanSegmentsResult, prune_orphan_segments
from wenyan.core.run.stale_assembly import prune_stale_assembly
from wenyan.jobs.context import JobContext, JobOptions
from wenyan_models.domain.ids import DocumentId
from wenyan_models.domain.results import JobOutcome, Promoted, Skipped


def run_prune_orphan_segments(
    ctx: JobContext,
    document_id: DocumentId,
    options: JobOptions,
) -> JobOutcome[PruneOrphanSegmentsResult]:
    result = prune_orphan_segments(
        ctx.artifacts,
        ctx.repo_root,
        document_id,
        dry_run=options.dry_run,
    )
    prune_stale_assembly(
        ctx.artifacts,
        ctx.repo_root,
        document_id,
        dry_run=options.dry_run,
    )
    if not result.removed:
        return Skipped(reason="no orphaned segments")
    return Promoted(artifact=result)
