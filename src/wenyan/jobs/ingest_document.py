import uuid
from pathlib import Path

from wenyan.core.ports.artifact_ref import normalized_document_ref
from wenyan.jobs.context import JobContext, JobOptions
from wenyan_models.domain.ids import DocumentId, document_id
from wenyan_models.domain.results import JobOutcome, Promoted, Skipped


def run_ingest_document(
    ctx: JobContext,
    source_dir: Path,
    options: JobOptions,
) -> JobOutcome[DocumentId]:
    slug = ctx.registry.source_slug_from_path(source_dir)
    entry = ctx.registry.resolve(str(slug))
    doc_id = entry.document_id or document_id(str(uuid.uuid4()))
    ref = normalized_document_ref(doc_id)
    if ctx.artifacts.exists(ref) and not options.force:
        return Skipped(reason="normalized document already exists")
    metadata = ctx.registry.load_document_yaml(slug)
    if options.dry_run:
        return Promoted(artifact=doc_id)
    ctx.normalized_text.write_from_source(
        doc_id,
        entry.title,
        ctx.registry.source_text_path(slug),
        metadata,
    )
    if entry.document_id is None:
        ctx.registry.assign_document_id(slug, doc_id)
    return Promoted(artifact=doc_id)
