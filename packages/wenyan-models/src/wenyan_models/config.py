from typing import Literal

from pydantic import BaseModel, Field

from wenyan_models.artifacts.base import DEFAULT_ARTIFACT_CONFIG

ModelProvider = Literal["mock", "anthropic", "minimax"]


class ProviderModelConfig(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    model: str


class MockModelConfig(ProviderModelConfig):
    model: str = "mock"
    fixture_dir: str = Field(default="tests/fixtures/llm", alias="fixtureDir")


class ModelsConfig(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    provider: ModelProvider = "mock"
    anthropic: ProviderModelConfig
    minimax: ProviderModelConfig
    mock: MockModelConfig = Field(default_factory=MockModelConfig)

    @property
    def active_model(self) -> str:
        if self.provider == "anthropic":
            return self.anthropic.model
        if self.provider == "minimax":
            return self.minimax.model
        return self.mock.model


class RetryConfig(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    max_attempts: int = Field(alias="maxAttempts")
    backoff_seconds: int = Field(alias="backoffSeconds")


class ConcurrencyConfig(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    default: int


class PromptsConfig(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    root: str


class PreprocessingConfig(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    models: ModelsConfig
    retry: RetryConfig
    concurrency: ConcurrencyConfig
    prompts: PromptsConfig
    anthropic_api_key: str | None = None
    minimax_api_key: str | None = None
