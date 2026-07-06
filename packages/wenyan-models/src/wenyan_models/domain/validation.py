from pydantic import BaseModel

from wenyan_models.artifacts.base import DEFAULT_ARTIFACT_CONFIG
from wenyan_models.domain.enums import ValidationStatus


class CheckResult(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    code: str
    message: str


class SpanValidationResult(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    status: ValidationStatus
    checks: tuple[CheckResult, ...] = ()
