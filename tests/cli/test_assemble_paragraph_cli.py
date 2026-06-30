from pathlib import Path

import pytest
from typer.testing import CliRunner

from tests.jobs.assembly_helpers import prepare_paragraph_with_complete_segments
from wenyan.cli import app


def test_assemble_paragraph_cli(
    tmp_workspace: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepare_paragraph_with_complete_segments(tmp_workspace)
    monkeypatch.chdir(tmp_workspace)
    result = CliRunner().invoke(
        app,
        [
            "preprocess",
            "assemble-paragraph",
            "sunzi-bingfa",
            "--chapter",
            "1",
            "--paragraph",
            "1",
        ],
    )
    assert result.exit_code == 0


def test_review_paragraph_assembly_cli(
    tmp_workspace: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepare_paragraph_with_complete_segments(tmp_workspace)
    monkeypatch.chdir(tmp_workspace)
    assemble = CliRunner().invoke(
        app,
        [
            "preprocess",
            "assemble-paragraph",
            "sunzi-bingfa",
            "--chapter",
            "1",
            "--paragraph",
            "1",
        ],
    )
    assert assemble.exit_code == 0
    review = CliRunner().invoke(
        app,
        [
            "preprocess",
            "review-paragraph-assembly",
            "sunzi-bingfa",
            "--chapter",
            "1",
            "--paragraph",
            "1",
        ],
    )
    assert review.exit_code == 0
