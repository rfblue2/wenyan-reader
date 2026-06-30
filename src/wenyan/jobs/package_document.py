from wenyan.core.gloss.glossary_draft import load_glossary_draft
from wenyan.core.package.build import build_document_package
from wenyan.core.package.collect import collect_ready_paragraphs
from wenyan.core.package.input_hash import package_input_hash
from wenyan.core.package.promote import plan_content_writes, promote_content_writes
from wenyan.core.package.validate import validate_document_package
from wenyan.core.ports.artifact_ref import normalized_document_ref, package_validation_ref
from wenyan.core.ports.artifact_store import ArtifactWrite
from wenyan.jobs.context import JobContext, JobOptions
from wenyan_models.artifacts.normalized import NormalizedDocument
from wenyan_models.artifacts.package import PackageValidationArtifact
from wenyan_models.domain.enums import ValidationStatus
from wenyan_models.domain.ids import DocumentId
from wenyan_models.domain.results import JobFailure, JobOutcome, Promoted, Skipped
from wenyan_models.reader.document import GlossIndex


def run_package_document(
    ctx: JobContext,
    document_id: DocumentId,
    options: JobOptions,
) -> JobOutcome[PackageValidationArtifact]:
    normalized_ref = normalized_document_ref(document_id)
    if not ctx.artifacts.exists(normalized_ref):
        return JobFailure(code="missing-input", message="normalized document is missing")
    normalized = ctx.artifacts.read(normalized_ref, NormalizedDocument)

    ready_paragraphs = collect_ready_paragraphs(ctx.artifacts, document_id)
    if not ready_paragraphs:
        return JobFailure(
            code="nothing-to-package",
            message="no paragraphs with passed assembly validation",
        )

    glossary = load_glossary_draft(ctx.artifacts, document_id)
    assembly_hashes = tuple(
        (str(item.paragraph_id), item.assembly_input_hash) for item in ready_paragraphs
    )
    input_hash = package_input_hash(
        normalized_hash=normalized.normalized_hash,
        glossary=glossary,
        paragraph_assembly_hashes=assembly_hashes,
    )

    validation_ref = package_validation_ref(document_id)
    if ctx.artifacts.exists(validation_ref) and not options.force:
        existing = ctx.artifacts.read(validation_ref, PackageValidationArtifact)
        if existing.input_hash == input_hash and existing.status == ValidationStatus.PASSED:
            return Skipped(reason="document package is current")

    gloss_index = GlossIndex(glosses=glossary.glosses)
    manifest, chapter_packages, paragraph_index = build_document_package(
        document_id,
        normalized.title,
        ready_paragraphs,
    )
    paragraph_packages = {
        paragraph_id_value: item.package for paragraph_id_value, item in paragraph_index.items()
    }
    validation = validate_document_package(
        manifest=manifest,
        gloss_index=gloss_index,
        chapter_packages=chapter_packages,
        paragraph_index=paragraph_index,
        input_hash=input_hash,
        paragraphs_packaged=len(ready_paragraphs),
    )
    if validation.status == ValidationStatus.FAILED:
        if not options.dry_run:
            ctx.artifacts.write(validation_ref, validation, dry_run=False)
        return JobFailure(
            code="validation-failed",
            message="document package validation failed",
        )

    if options.dry_run:
        return Promoted(artifact=validation)

    content_writes = plan_content_writes(
        ctx.repo_root,
        document_id,
        manifest,
        gloss_index,
        chapter_packages,
        paragraph_packages,
    )
    promote_content_writes(content_writes, dry_run=False)
    ctx.artifacts.write(validation_ref, validation, dry_run=False)
    return Promoted(artifact=validation)
