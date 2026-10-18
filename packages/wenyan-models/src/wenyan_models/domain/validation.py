from collections.abc import Iterable, Sequence
from typing import Self

from pydantic import BaseModel, model_validator

from wenyan_models.base import DEFAULT_ARTIFACT_CONFIG
from wenyan_models.domain.enums import ValidationStatus


class CheckResult(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    code: str
    message: str


def validation_status(checks: Sequence[CheckResult]) -> ValidationStatus:
    """`PASSED` iff there are no failed checks. Every validation artifact derives status this way."""
    return ValidationStatus.FAILED if checks else ValidationStatus.PASSED


class ValidationReport(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    status: ValidationStatus
    checks: tuple[CheckResult, ...] = ()

    @classmethod
    def from_checks(cls, checks: Iterable[CheckResult] = ()) -> Self:
        checks = tuple(checks)
        return cls(status=validation_status(checks), checks=checks)

    @model_validator(mode="after")
    def check_status(self) -> Self:
        if self.status != validation_status(self.checks):
            raise ValueError("status must be failed iff checks are present")
        return self
