from pydantic import BaseModel, ConfigDict, Field

_DEFAULT_MODEL_CONFIG = ConfigDict(frozen=True, populate_by_name=True, extra="forbid")


class ModelsConfig(BaseModel):
    model_config = _DEFAULT_MODEL_CONFIG

    primary: str


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
