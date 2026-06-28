from pydantic import BaseModel, ConfigDict

from wenyan_models.domain.enums import ValidationStatus

_DEFAULT_MODEL_CONFIG = ConfigDict(frozen=True, populate_by_name=True, extra="forbid")


class CheckResult(BaseModel):
    model_config = _DEFAULT_MODEL_CONFIG

    code: str
    message: str


class SpanValidationResult(BaseModel):
    model_config = _DEFAULT_MODEL_CONFIG

    status: ValidationStatus
    checks: tuple[CheckResult, ...] = ()
