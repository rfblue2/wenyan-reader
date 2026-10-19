from pathlib import Path

from wenyan.core.ports.artifact_ref import DocumentArtifactKind, DocumentRef
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
    chapter_proposal = ctx.artifacts.read(
        DocumentRef(DocumentArtifactKind.CHAPTER_PROPOSAL, doc_id),
        ChapterProposal,
    )
    chapter_id_value = chapter_proposal.chapters[0].id

    outcome = run_package_document(ctx, doc_id, JobOptions())
    assert isinstance(outcome, Promoted)
    assert outcome.artifact.paragraphs_packaged == 1
    assert outcome.artifact.status.value == "passed"

    content_root = tmp_workspace / "content" / "documents" / str(doc_id)
    assert content_root.is_dir()
    assert (content_root / "document.json").is_file()
    assert (content_root / "glosses" / "index.json").is_file()
    chapter_root = content_root / "chapters" / str(chapter_id_value)
    assert (chapter_root / "chapter.json").is_file()
    assert (chapter_root / "paragraphs" / f"{paragraph_id_value}.json").is_file()
    validation = ctx.artifacts.read(
        DocumentRef(DocumentArtifactKind.PACKAGE_VALIDATION, doc_id),
        PackageValidationArtifact,
    )
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
