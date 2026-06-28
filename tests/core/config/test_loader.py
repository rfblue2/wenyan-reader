import pytest

from wenyan.core.config.loader import load_preprocessing_config


def test_env_overrides_yaml(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "preprocessing.yaml").write_text(
        "models:\n  primary: from-yaml\n"
        "retry:\n  maxAttempts: 3\n  backoffSeconds: 2\n"
        "concurrency:\n  default: 4\n"
        "prompts:\n  root: prompts\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("WENYAN_MODEL_PRIMARY", "from-env")

    config = load_preprocessing_config(tmp_path)

    assert config.models.primary == "from-env"


def test_local_override_merges_yaml(tmp_path) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "preprocessing.yaml").write_text(
        "models:\n  primary: base-model\n"
        "retry:\n  maxAttempts: 3\n  backoffSeconds: 2\n"
        "concurrency:\n  default: 4\n"
        "prompts:\n  root: prompts\n",
        encoding="utf-8",
    )
    override_dir = tmp_path / ".wenyan"
    override_dir.mkdir()
    (override_dir / "config.yaml").write_text(
        "concurrency:\n  default: 8\n",
        encoding="utf-8",
    )

    config = load_preprocessing_config(tmp_path)

    assert config.models.primary == "base-model"
    assert config.concurrency.default == 8
