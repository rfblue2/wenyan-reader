from pathlib import Path

from wenyan.core.ports.artifact_ref import paragraph_assembly_review_ref
from wenyan.jobs.assemble_paragraph import run_assemble_paragraph
from wenyan.jobs.context import JobOptions
from wenyan.jobs.review_paragraph_assembly import run_review_paragraph_assembly
from wenyan_models.artifacts.assembly import ParagraphAssemblyReviewArtifact
from wenyan_models.domain.enums import ReviewStatus
from wenyan_models.domain.results import JobFailure, Promoted, Skipped, outcome_exit_code

from tests.jobs.assembly_helpers import prepare_paragraph_with_complete_segments


def test_review_paragraph_assembly_approves(tmp_workspace: Path) -> None:
    ctx, doc_id, paragraph_id_value = prepare_paragraph_with_complete_segments(tmp_workspace)
    run_assemble_paragraph(ctx, doc_id, paragraph_id_value, JobOptions())

    outcome = run_review_paragraph_assembly(ctx, doc_id, paragraph_id_value, JobOptions())
    assert outcome_exit_code(outcome) == 0
    assert isinstance(outcome, Promoted)
    review = ctx.artifacts.read(
        paragraph_assembly_review_ref(doc_id, paragraph_id_value),
        ParagraphAssemblyReviewArtifact,
    )
    assert review.status == ReviewStatus.APPROVED


def test_review_paragraph_assembly_skips_current(tmp_workspace: Path) -> None:
    ctx, doc_id, paragraph_id_value = prepare_paragraph_with_complete_segments(tmp_workspace)
    run_assemble_paragraph(ctx, doc_id, paragraph_id_value, JobOptions())
    run_review_paragraph_assembly(ctx, doc_id, paragraph_id_value, JobOptions())

    outcome = run_review_paragraph_assembly(ctx, doc_id, paragraph_id_value, JobOptions())
    assert isinstance(outcome, Skipped)


def test_review_paragraph_assembly_missing_package(tmp_workspace: Path) -> None:
    ctx, doc_id, paragraph_id_value = prepare_paragraph_with_complete_segments(tmp_workspace)

    outcome = run_review_paragraph_assembly(ctx, doc_id, paragraph_id_value, JobOptions())
    assert isinstance(outcome, JobFailure)
    assert outcome.code == "missing-input"


def test_review_paragraph_assembly_rejects(tmp_workspace: Path, monkeypatch) -> None:
    from wenyan.core.adapters import mock_llm_client

    original = mock_llm_client.MockLLMClient.complete_model

    def reject_review(self, prompt, model):  # type: ignore[no-untyped-def]
        result = original(self, prompt, model)
        if prompt.template_name == "review-paragraph-assembly":
            return result.model_copy(update={"status": ReviewStatus.REJECTED})
        return result

    monkeypatch.setattr(mock_llm_client.MockLLMClient, "complete_model", reject_review)

    ctx, doc_id, paragraph_id_value = prepare_paragraph_with_complete_segments(tmp_workspace)
    run_assemble_paragraph(ctx, doc_id, paragraph_id_value, JobOptions())

    outcome = run_review_paragraph_assembly(ctx, doc_id, paragraph_id_value, JobOptions())
    assert isinstance(outcome, JobFailure)
    assert outcome.code == "review-rejected"
    review = ctx.artifacts.read(
        paragraph_assembly_review_ref(doc_id, paragraph_id_value),
        ParagraphAssemblyReviewArtifact,
    )
    assert review.status == ReviewStatus.REJECTED
