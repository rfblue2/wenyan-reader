from pathlib import Path

from wenyan.bootstrap import build_job_context
from wenyan.core.ports.artifact_ref import (
    paragraph_assembly_package_ref,
    paragraph_assembly_validation_ref,
)
from wenyan.jobs.assemble_paragraph import run_assemble_paragraph
from wenyan.jobs.context import JobOptions
from wenyan.jobs.ingest_document import run_ingest_document
from wenyan.jobs.split_paragraphs import run_split_paragraphs
from wenyan.jobs.split_segments import run_split_segments
from wenyan.jobs.tokenize_segment import run_tokenize_segment
from wenyan_models.artifacts.assembly import ParagraphAssemblyValidationArtifact
from wenyan_models.domain.ids import paragraph_id
from wenyan_models.domain.results import JobFailure, Promoted, Skipped, outcome_exit_code
from wenyan_models.domain.targets import single_segment_target
from wenyan_models.reader.paragraph import ParagraphPackage
from conftest import install_sunzi_chapter_proposal

from tests.jobs.assembly_helpers import prepare_paragraph_with_complete_segments


def test_assemble_paragraph_writes_package_and_validation(tmp_workspace: Path) -> None:
    ctx, doc_id, paragraph_id_value = prepare_paragraph_with_complete_segments(tmp_workspace)

    outcome = run_assemble_paragraph(ctx, doc_id, paragraph_id_value, JobOptions())
    assert outcome_exit_code(outcome) == 0
    assert isinstance(outcome, Promoted)
    package_ref = paragraph_assembly_package_ref(doc_id, paragraph_id_value)
    validation_ref = paragraph_assembly_validation_ref(doc_id, paragraph_id_value)
    assert ctx.artifacts.exists(package_ref)
    assert ctx.artifacts.exists(validation_ref)
    package = ctx.artifacts.read(package_ref, ParagraphPackage)
    assert package.segments


def test_assemble_paragraph_skips_current(tmp_workspace: Path) -> None:
    ctx, doc_id, paragraph_id_value = prepare_paragraph_with_complete_segments(tmp_workspace)
    run_assemble_paragraph(ctx, doc_id, paragraph_id_value, JobOptions())

    outcome = run_assemble_paragraph(ctx, doc_id, paragraph_id_value, JobOptions())
    assert isinstance(outcome, Skipped)


def test_assemble_paragraph_blocked_upstream(tmp_workspace: Path) -> None:
    ctx = build_job_context(tmp_workspace)
    source_dir = tmp_workspace / "sources" / "documents" / "sunzi-bingfa"
    doc_id = run_ingest_document(ctx, source_dir, JobOptions()).artifact  # type: ignore[union-attr]
    chapter_proposal = install_sunzi_chapter_proposal(ctx, doc_id)
    chapter_id_value = chapter_proposal.chapters[0].id
    paragraphs = run_split_paragraphs(ctx, doc_id, chapter_id_value, JobOptions()).artifact  # type: ignore[union-attr]
    paragraph_id_value = paragraphs.paragraphs[0].id
    draft = run_split_segments(ctx, doc_id, paragraph_id_value, JobOptions()).artifact  # type: ignore[union-attr]
    run_tokenize_segment(ctx, doc_id, single_segment_target(draft.segments[0].id), JobOptions())

    outcome = run_assemble_paragraph(ctx, doc_id, paragraph_id_value, JobOptions())
    assert isinstance(outcome, JobFailure)
    assert outcome.code == "blocked-upstream"


def test_assemble_paragraph_missing_draft(tmp_workspace: Path) -> None:
    ctx = build_job_context(tmp_workspace)
    source_dir = tmp_workspace / "sources" / "documents" / "sunzi-bingfa"
    doc_id = run_ingest_document(ctx, source_dir, JobOptions()).artifact  # type: ignore[union-attr]

    outcome = run_assemble_paragraph(
        ctx,
        doc_id,
        paragraph_id("00000000-0000-0000-0000-000000000099"),
        JobOptions(),
    )
    assert isinstance(outcome, JobFailure)
    assert outcome.code == "missing-input"
