from pathlib import Path

from wenyan.core.package.paths import (
    content_chapter_manifest_path,
    content_document_manifest_path,
    content_gloss_index_path,
    content_paragraph_path,
)
from wenyan.core.ports.artifact_ref import chapter_proposal_ref, package_validation_ref
from wenyan.jobs.assemble_paragraph import run_assemble_paragraph
from wenyan.jobs.context import JobOptions
from wenyan.jobs.package_document import run_package_document
from wenyan_models.artifacts.package import PackageValidationArtifact
from wenyan_models.artifacts.structure import ChapterProposal
from wenyan_models.domain.results import JobFailure, Promoted, Skipped

from tests.jobs.assembly_helpers import prepare_paragraph_with_complete_segments


def test_package_document_writes_content_files(tmp_workspace: Path) -> None:
    ctx, doc_id, paragraph_id_value = prepare_paragraph_with_complete_segments(tmp_workspace)
    run_assemble_paragraph(ctx, doc_id, paragraph_id_value, JobOptions())
    chapter_id_value = ctx.artifacts.read(chapter_proposal_ref(doc_id), ChapterProposal).chapters[0].id

    outcome = run_package_document(ctx, doc_id, JobOptions())
    assert isinstance(outcome, Promoted)
    assert outcome.artifact.paragraphs_packaged == 1
    assert outcome.artifact.status.value == "passed"

    content_root = tmp_workspace / "content" / "documents" / str(doc_id)
    assert content_root.is_dir()
    assert content_document_manifest_path(tmp_workspace, doc_id).is_file()
    assert content_gloss_index_path(tmp_workspace, doc_id).is_file()
    assert content_chapter_manifest_path(tmp_workspace, doc_id, chapter_id_value).is_file()
    assert content_paragraph_path(
        tmp_workspace,
        doc_id,
        chapter_id_value,
        paragraph_id_value,
    ).is_file()
    validation = ctx.artifacts.read(package_validation_ref(doc_id), PackageValidationArtifact)
    assert validation.status.value == "passed"


def test_package_document_skips_when_current(tmp_workspace: Path) -> None:
    ctx, doc_id, paragraph_id_value = prepare_paragraph_with_complete_segments(tmp_workspace)
    run_assemble_paragraph(ctx, doc_id, paragraph_id_value, JobOptions())
    run_package_document(ctx, doc_id, JobOptions())

    outcome = run_package_document(ctx, doc_id, JobOptions())
    assert isinstance(outcome, Skipped)


def test_package_document_fails_without_ready_paragraphs(tmp_workspace: Path) -> None:
    ctx, doc_id, _paragraph_id_value = prepare_paragraph_with_complete_segments(tmp_workspace)

    outcome = run_package_document(ctx, doc_id, JobOptions())
    assert isinstance(outcome, JobFailure)
    assert outcome.code == "nothing-to-package"
