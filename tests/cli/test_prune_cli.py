from pathlib import Path

import pytest
from typer.testing import CliRunner

from tests.core.run.test_orphan_segments import _prepare_paragraph_with_segments
from wenyan.cli import app
from wenyan.jobs.context import JobOptions
from wenyan.jobs.split_segments import run_split_segments


def test_prune_cli_removes_orphaned_segments(
    tmp_workspace: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ctx, doc_id, paragraph_id_value, first_draft = _prepare_paragraph_with_segments(tmp_workspace)
    stale_segment_ids = {segment.id for segment in first_draft.segments}

    run_split_segments(ctx, doc_id, paragraph_id_value, JobOptions(force=True))

    monkeypatch.chdir(tmp_workspace)
    result = CliRunner().invoke(app, ["preprocess", "prune", "sunzi-bingfa"])

    assert result.exit_code == 0, result.output
    assert "removed" in result.output.lower()
    for segment_id_value in stale_segment_ids:
        assert str(segment_id_value) in result.output
