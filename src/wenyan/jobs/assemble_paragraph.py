from wenyan.core.assembly.compile_paragraph import compile_paragraph_package
from wenyan.core.assembly.input_hash import assembly_input_hash, segment_output_hash
from wenyan.core.assembly.load_segment_outputs import (
    MissingSegmentOutputError,
    load_all_segment_outputs,
)
from wenyan.core.assembly.validate_package import validate_paragraph_package
from wenyan.core.ports.artifact_ref import (
    paragraph_assembly_package_ref,
    paragraph_assembly_validation_ref,
    paragraph_draft_ref,
)
from wenyan.core.ports.artifact_store import ArtifactWrite
from wenyan.core.run.segment_pipeline import pending_segment_subjobs
from wenyan.jobs.context import JobContext, JobOptions
from wenyan_models.artifacts.assembly import ParagraphAssemblyValidationArtifact
from wenyan_models.artifacts.paragraph import ParagraphDraft
from wenyan_models.domain.enums import ValidationStatus
from wenyan_models.domain.ids import DocumentId, ParagraphId
from wenyan_models.domain.results import JobFailure, JobOutcome, Promoted, Skipped
from wenyan_models.reader.paragraph import ParagraphPackage


def run_assemble_paragraph(
    ctx: JobContext,
    document_id: DocumentId,
    paragraph_id_value: ParagraphId,
    options: JobOptions,
) -> JobOutcome[ParagraphPackage]:
    draft_ref = paragraph_draft_ref(document_id, paragraph_id_value)
    if not ctx.artifacts.exists(draft_ref):
        return JobFailure(code="missing-input", message="paragraph draft is missing")
    draft = ctx.artifacts.read(draft_ref, ParagraphDraft)
    for segment in draft.segments:
        if pending_segment_subjobs(ctx.artifacts, document_id, segment.id):
            return JobFailure(
                code="blocked-upstream",
                message=f"segment {segment.id} is incomplete",
            )
    try:
        outputs = load_all_segment_outputs(ctx.artifacts, document_id, draft)
    except MissingSegmentOutputError as exc:
        return JobFailure(code="missing-input", message=str(exc))
    segment_hashes = {str(output.segment_id): segment_output_hash(output) for output in outputs}
    input_hash = assembly_input_hash(draft, segment_hashes)
    package_ref = paragraph_assembly_package_ref(document_id, paragraph_id_value)
    validation_ref = paragraph_assembly_validation_ref(document_id, paragraph_id_value)
    if (
        ctx.artifacts.exists(package_ref)
        and ctx.artifacts.exists(validation_ref)
        and not options.force
    ):
        existing = ctx.artifacts.read(validation_ref, ParagraphAssemblyValidationArtifact)
        if existing.input_hash == input_hash and existing.status == ValidationStatus.PASSED:
            return Skipped(reason="paragraph assembly is current")
    package = compile_paragraph_package(draft, outputs)
    validation = validate_paragraph_package(draft, outputs, package)
    if validation.status == ValidationStatus.FAILED:
        if not options.dry_run:
            ctx.artifacts.write(validation_ref, validation, dry_run=False)
        return JobFailure(
            code="validation-failed",
            message="paragraph assembly validation failed",
        )
    if options.dry_run:
        return Promoted(artifact=package)
    ctx.artifacts.write_batch(
        [
            ArtifactWrite(ref=package_ref, payload=package),
            ArtifactWrite(ref=validation_ref, payload=validation),
        ],
        dry_run=False,
    )
    return Promoted(artifact=package)
