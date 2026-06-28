from typer.testing import CliRunner

from wenyan.cli import app


def test_help() -> None:
    result = CliRunner().invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "preprocess" in result.stdout
