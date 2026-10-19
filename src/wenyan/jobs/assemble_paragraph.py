from wenyan.core.assembly.compile_paragraph import compile_paragraph_package
from wenyan.core.assembly.state import AssemblyState, SegmentsIncomplete, inspect_paragraph_assembly
from wenyan.core.assembly.validate_package import validate_paragraph_package
from wenyan.core.ports.artifact_ref import ParagraphArtifactKind, ParagraphRef
from wenyan.core.ports.artifact_store import ArtifactWrite
from wenyan.jobs.context import JobContext, JobOptions
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
    assembly = inspect_paragraph_assembly(ctx.artifacts, document_id, paragraph_id_value)
    match assembly:
        case None:
            return JobFailure(code="missing-input", message="paragraph draft is missing")
        case SegmentsIncomplete(segment_id=incomplete):
            return JobFailure(
                code="blocked-upstream",
                message=f"segment {incomplete} is incomplete",
            )
    if assembly.state == AssemblyState.CURRENT and not options.force:
        return Skipped(reason="paragraph assembly is current")
    package = compile_paragraph_package(assembly.draft, assembly.segments)
    validation = validate_paragraph_package(assembly.draft, package, input_hash=assembly.input_hash)
    package_ref = ParagraphRef(
        ParagraphArtifactKind.ASSEMBLY_PACKAGE, document_id, paragraph_id_value
    )
    validation_ref = ParagraphRef(
        ParagraphArtifactKind.ASSEMBLY_VALIDATION, document_id, paragraph_id_value
    )
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
