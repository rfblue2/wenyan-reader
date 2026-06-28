import pytest

from wenyan.core.config.loader import load_preprocessing_config

_BASE_YAML = (
    "models:\n"
    "  provider: mock\n"
    "  anthropic:\n"
    "    model: claude-from-yaml\n"
    "  minimax:\n"
    "    model: MiniMax-from-yaml\n"
    "retry:\n  maxAttempts: 3\n  backoffSeconds: 2\n"
    "concurrency:\n  default: 4\n"
    "prompts:\n  root: prompts\n"
)


def test_model_override_for_active_provider(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "preprocessing.yaml").write_text(_BASE_YAML, encoding="utf-8")
    monkeypatch.setenv("WENYAN_MODEL", "custom-mock-model")

    config = load_preprocessing_config(tmp_path)

    assert config.models.provider == "mock"
    assert config.models.mock.model == "custom-mock-model"
    assert config.models.active_model == "custom-mock-model"


def test_model_override_follows_provider_switch(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "preprocessing.yaml").write_text(_BASE_YAML, encoding="utf-8")
    monkeypatch.setenv("WENYAN_MODEL_PROVIDER", "minimax")
    monkeypatch.setenv("WENYAN_MODEL", "MiniMax-from-env")

    config = load_preprocessing_config(tmp_path)

    assert config.models.provider == "minimax"
    assert config.models.minimax.model == "MiniMax-from-env"
    assert config.models.active_model == "MiniMax-from-env"


def test_minimax_api_key_from_env(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "preprocessing.yaml").write_text(_BASE_YAML, encoding="utf-8")
    monkeypatch.setenv("MINIMAX_API_KEY", "minimax-secret")

    config = load_preprocessing_config(tmp_path)

    assert config.minimax_api_key == "minimax-secret"


def test_local_override_merges_yaml(tmp_path) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "preprocessing.yaml").write_text(_BASE_YAML, encoding="utf-8")
    override_dir = tmp_path / ".wenyan"
    override_dir.mkdir()
    (override_dir / "config.yaml").write_text(
        "concurrency:\n  default: 8\n",
        encoding="utf-8",
    )

    config = load_preprocessing_config(tmp_path)

    assert config.models.anthropic.model == "claude-from-yaml"
    assert config.models.active_model == "mock"
    assert config.concurrency.default == 8
