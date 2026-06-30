from pathlib import Path

from wenyan.core.adapters.filesystem_status_reader import FilesystemStatusReader
from wenyan.core.status.derivation import _rollup_paragraph_status
from wenyan.jobs.assemble_paragraph import run_assemble_paragraph
from wenyan.jobs.context import JobOptions
from wenyan_models.domain.enums import UnitStatus

from tests.jobs.assembly_helpers import prepare_paragraph_with_complete_segments


def test_paragraph_not_complete_when_segments_done_but_assembly_pending(tmp_workspace: Path) -> None:
    ctx, doc_id, paragraph_id_value = prepare_paragraph_with_complete_segments(tmp_workspace)
    reader = FilesystemStatusReader(ctx.artifacts, tmp_workspace)
    payload = reader.paragraph_status(doc_id, paragraph_id_value)

    assert payload.assembly is not None
    assert payload.assembly.status == UnitStatus.PENDING
    assert _rollup_paragraph_status(payload) == UnitStatus.IN_PROGRESS


def test_paragraph_complete_after_assemble(tmp_workspace: Path) -> None:
    ctx, doc_id, paragraph_id_value = prepare_paragraph_with_complete_segments(tmp_workspace)
    run_assemble_paragraph(ctx, doc_id, paragraph_id_value, JobOptions())
    reader = FilesystemStatusReader(ctx.artifacts, tmp_workspace)
    payload = reader.paragraph_status(doc_id, paragraph_id_value)

    assert payload.assembly is not None
    assert payload.assembly.status == UnitStatus.COMPLETE
    assert _rollup_paragraph_status(payload) == UnitStatus.COMPLETE
