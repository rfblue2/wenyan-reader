import os
from pathlib import Path
from typing import Any

import yaml

from wenyan_models.config import PreprocessingConfig


def load_preprocessing_config(repo_root: Path) -> PreprocessingConfig:
    merged = _load_yaml(repo_root / "config" / "preprocessing.yaml")
    override_path = _override_path(repo_root)
    if override_path is not None:
        merged = _deep_merge(merged, _load_yaml(override_path))
    merged = _deep_merge(merged, _env_overrides(merged))
    return PreprocessingConfig.model_validate(merged)


def _override_path(repo_root: Path) -> Path | None:
    env_path = os.environ.get("WENYAN_CONFIG")
    if env_path:
        return Path(env_path)
    local = repo_root / ".wenyan" / "config.yaml"
    if local.is_file():
        return local
    return None


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if loaded is None:
        return {}
    if not isinstance(loaded, dict):
        raise ValueError(f"expected mapping in {path}")
    return loaded


def _env_overrides(merged: dict[str, Any]) -> dict[str, Any]:
    overrides: dict[str, Any] = {}
    models: dict[str, Any] = {}
    if provider := os.environ.get("WENYAN_MODEL_PROVIDER"):
        models["provider"] = provider
    if model := os.environ.get("WENYAN_MODEL"):
        effective_provider = models.get("provider") or merged.get("models", {}).get("provider", "mock")
        models.setdefault(effective_provider, {})["model"] = model
    if models:
        overrides["models"] = models
    if api_key := os.environ.get("ANTHROPIC_API_KEY"):
        overrides["anthropic_api_key"] = api_key
    if api_key := os.environ.get("MINIMAX_API_KEY"):
        overrides["minimax_api_key"] = api_key
    return overrides


def _deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in overlay.items():
        existing = merged.get(key)
        if isinstance(existing, dict) and isinstance(value, dict):
            merged[key] = _deep_merge(existing, value)
        else:
            merged[key] = value
    return merged
