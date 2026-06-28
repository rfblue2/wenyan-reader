import os
from pathlib import Path

from wenyan.core.adapters.anthropic_llm_client import AnthropicLLMClient
from wenyan.core.adapters.filesystem_artifact_store import FilesystemArtifactStore
from wenyan.core.adapters.mock_llm_client import MockLLMClient
from wenyan.core.adapters.pure_span_validator import PureSpanValidator
from wenyan.core.adapters.yaml_source_registry import YamlSourceRegistry
from wenyan.core.config.loader import load_preprocessing_config
from wenyan.core.ports.llm_client import LLMClient
from wenyan.jobs.context import JobContext


def build_job_context(repo_root: Path) -> JobContext:
    config = load_preprocessing_config(repo_root)
    llm_client = os.environ.get("WENYAN_LLM_CLIENT", "mock")
    llm: LLMClient
    if llm_client == "anthropic":
        if not config.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY is required for anthropic LLM client")
        llm = AnthropicLLMClient(config.anthropic_api_key, config.models.primary)
    else:
        llm = MockLLMClient(repo_root / "tests" / "fixtures" / "llm")
    return JobContext(
        repo_root=repo_root,
        config=config,
        artifacts=FilesystemArtifactStore(repo_root),
        registry=YamlSourceRegistry(repo_root),
        llm=llm,
        spans=PureSpanValidator(),
    )
