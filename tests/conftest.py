from pathlib import Path
import shutil

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def tmp_workspace(tmp_path: Path) -> Path:
    workspace = tmp_path / "repo"
    shutil.copytree(REPO_ROOT / "sources", workspace / "sources")
    (workspace / "config").mkdir()
    shutil.copy(REPO_ROOT / "config/preprocessing.yaml", workspace / "config/preprocessing.yaml")
    (workspace / "preprocess").mkdir()
    (workspace / "content").mkdir()
    return workspace
