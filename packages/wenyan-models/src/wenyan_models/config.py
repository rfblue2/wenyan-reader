from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

_DEFAULT_MODEL_CONFIG = ConfigDict(frozen=True, populate_by_name=True, extra="forbid")

ModelProvider = Literal["mock", "anthropic", "minimax"]


class ProviderModelConfig(BaseModel):
    model_config = _DEFAULT_MODEL_CONFIG

    model: str


class ModelsConfig(BaseModel):
    model_config = _DEFAULT_MODEL_CONFIG

    provider: ModelProvider = "mock"
    anthropic: ProviderModelConfig
    minimax: ProviderModelConfig
    mock: ProviderModelConfig = Field(
        default_factory=lambda: ProviderModelConfig(model="mock"),
    )

    @property
    def active_model(self) -> str:
        if self.provider == "anthropic":
            return self.anthropic.model
        if self.provider == "minimax":
            return self.minimax.model
        return self.mock.model


class RetryConfig(BaseModel):
    model_config = _DEFAULT_MODEL_CONFIG

    max_attempts: int = Field(alias="maxAttempts")
    backoff_seconds: int = Field(alias="backoffSeconds")


class ConcurrencyConfig(BaseModel):
    model_config = _DEFAULT_MODEL_CONFIG

    default: int


class PromptsConfig(BaseModel):
    model_config = _DEFAULT_MODEL_CONFIG

    root: str


class PreprocessingConfig(BaseModel):
    model_config = _DEFAULT_MODEL_CONFIG

    models: ModelsConfig
    retry: RetryConfig
    concurrency: ConcurrencyConfig
    prompts: PromptsConfig
    anthropic_api_key: str | None = None
    minimax_api_key: str | None = None
