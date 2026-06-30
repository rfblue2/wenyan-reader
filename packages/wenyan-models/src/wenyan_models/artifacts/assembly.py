from pydantic import BaseModel, Field

from wenyan_models.artifacts.base import (
    DEFAULT_ARTIFACT_CONFIG,
    ContentHashField,
    ParagraphIdField,
)
from wenyan_models.domain.enums import ValidationStatus
from wenyan_models.domain.validation import CheckResult


class ParagraphAssemblyValidationArtifact(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    paragraph_id: ParagraphIdField = Field(alias="paragraphId")
    input_hash: ContentHashField = Field(alias="inputHash")
    status: ValidationStatus
    checks: tuple[CheckResult, ...] = ()
