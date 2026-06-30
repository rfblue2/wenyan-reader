from pathlib import Path

from wenyan.core.adapters.filesystem_status_reader import FilesystemStatusReader
from wenyan.core.status.derivation import _rollup_paragraph_status
from wenyan.jobs.assemble_paragraph import run_assemble_paragraph
from wenyan.jobs.context import JobOptions
from wenyan.jobs.review_paragraph_assembly import run_review_paragraph_assembly
from wenyan_models.domain.enums import UnitStatus

from tests.jobs.assembly_helpers import prepare_paragraph_with_complete_segments


def test_paragraph_not_complete_when_segments_done_but_assembly_pending(tmp_workspace: Path) -> None:
    ctx, doc_id, paragraph_id_value = prepare_paragraph_with_complete_segments(tmp_workspace)
    reader = FilesystemStatusReader(ctx.artifacts, tmp_workspace)
    payload = reader.paragraph_status(doc_id, paragraph_id_value)

    assert payload.assembly is not None
    assert payload.assembly.assemble.status == UnitStatus.PENDING
    assert payload.assembly.review.status == UnitStatus.PENDING
    assert _rollup_paragraph_status(payload) == UnitStatus.IN_PROGRESS


def test_paragraph_in_progress_after_assemble_before_review(tmp_workspace: Path) -> None:
    ctx, doc_id, paragraph_id_value = prepare_paragraph_with_complete_segments(tmp_workspace)
    run_assemble_paragraph(ctx, doc_id, paragraph_id_value, JobOptions())
    reader = FilesystemStatusReader(ctx.artifacts, tmp_workspace)
    payload = reader.paragraph_status(doc_id, paragraph_id_value)

    assert payload.assembly is not None
    assert payload.assembly.assemble.status == UnitStatus.COMPLETE
    assert payload.assembly.review.status == UnitStatus.PENDING
    assert _rollup_paragraph_status(payload) == UnitStatus.IN_PROGRESS


def test_paragraph_complete_after_assembly_and_review(tmp_workspace: Path) -> None:
    ctx, doc_id, paragraph_id_value = prepare_paragraph_with_complete_segments(tmp_workspace)
    run_assemble_paragraph(ctx, doc_id, paragraph_id_value, JobOptions())
    run_review_paragraph_assembly(ctx, doc_id, paragraph_id_value, JobOptions())
    reader = FilesystemStatusReader(ctx.artifacts, tmp_workspace)
    payload = reader.paragraph_status(doc_id, paragraph_id_value)

    assert payload.assembly is not None
    assert payload.assembly.review.status == UnitStatus.COMPLETE
    assert _rollup_paragraph_status(payload) == UnitStatus.COMPLETE


def test_paragraph_blocked_when_assembly_review_rejected(tmp_workspace: Path, monkeypatch) -> None:
    from wenyan.core.adapters import mock_llm_client
    from wenyan_models.domain.enums import ReviewStatus

    original = mock_llm_client.MockLLMClient.complete_model

    def reject_review(self, prompt, model):  # type: ignore[no-untyped-def]
        result = original(self, prompt, model)
        if prompt.template_name == "review-paragraph-assembly":
            return result.model_copy(update={"status": ReviewStatus.REJECTED})
        return result

    monkeypatch.setattr(mock_llm_client.MockLLMClient, "complete_model", reject_review)

    ctx, doc_id, paragraph_id_value = prepare_paragraph_with_complete_segments(tmp_workspace)
    run_assemble_paragraph(ctx, doc_id, paragraph_id_value, JobOptions())
    run_review_paragraph_assembly(ctx, doc_id, paragraph_id_value, JobOptions())
    reader = FilesystemStatusReader(ctx.artifacts, tmp_workspace)
    payload = reader.paragraph_status(doc_id, paragraph_id_value)

    assert payload.assembly is not None
    assert payload.assembly.review.status == UnitStatus.BLOCKED
    assert _rollup_paragraph_status(payload) == UnitStatus.BLOCKED
