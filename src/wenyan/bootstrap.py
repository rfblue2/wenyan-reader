from pathlib import Path

from wenyan.core.adapters.anthropic_llm_client import AnthropicLLMClient
from wenyan.core.adapters.filesystem_artifact_store import FilesystemArtifactStore
from wenyan.core.adapters.filesystem_normalized_text_store import FilesystemNormalizedTextStore
from wenyan.core.adapters.minimax_llm_client import MiniMaxLLMClient
from wenyan.core.adapters.mock_llm_client import MockLLMClient
from wenyan.core.adapters.pure_span_validator import PureSpanValidator
from wenyan.core.adapters.yaml_source_registry import YamlSourceRegistry
from wenyan.core.config.loader import load_preprocessing_config
from wenyan.core.ports.llm_client import LLMClient
from wenyan.jobs.context import JobContext
from wenyan_models.config import PreprocessingConfig


def build_job_context(repo_root: Path) -> JobContext:
    config = load_preprocessing_config(repo_root)
    artifacts = FilesystemArtifactStore(repo_root)
    return JobContext(
        repo_root=repo_root,
        config=config,
        artifacts=artifacts,
        normalized_text=FilesystemNormalizedTextStore(repo_root, artifacts),
        registry=YamlSourceRegistry(repo_root),
        llm=_build_llm_client(config, repo_root),
        spans=PureSpanValidator(),
    )


def _build_llm_client(config: PreprocessingConfig, repo_root: Path) -> LLMClient:
    provider = config.models.provider
    model = config.models.active_model
    if provider == "anthropic":
        if not config.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY is required when models.provider is anthropic")
        return AnthropicLLMClient(config.anthropic_api_key, model)
    if provider == "minimax":
        if not config.minimax_api_key:
            raise ValueError("MINIMAX_API_KEY is required when models.provider is minimax")
        return MiniMaxLLMClient(config.minimax_api_key, model)
    return MockLLMClient(repo_root / "tests" / "fixtures" / "llm")
