from typing import Self

from pydantic import BaseModel, Field, model_validator

from wenyan_models.base import DEFAULT_ARTIFACT_CONFIG
from wenyan_models.domain.enums import ValidationStatus
from wenyan_models.domain.ids import ContentHashField, ParagraphIdField
from wenyan_models.domain.validation import CheckResult, validation_status


class ParagraphAssemblyValidationArtifact(BaseModel):
    """Not a `ValidationReport` subclass: inheritance would move `status`/`checks` ahead of the id fields on disk."""

    model_config = DEFAULT_ARTIFACT_CONFIG

    paragraph_id: ParagraphIdField = Field(alias="paragraphId")
    input_hash: ContentHashField = Field(alias="inputHash")
    status: ValidationStatus
    checks: tuple[CheckResult, ...] = ()

    @model_validator(mode="after")
    def check_status(self) -> Self:
        if self.status != validation_status(self.checks):
            raise ValueError("status must be failed iff checks are present")
        return self
