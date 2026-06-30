from pydantic import BaseModel, Field

from wenyan_models.artifacts.base import (
    DEFAULT_ARTIFACT_CONFIG,
    ContentHashField,
    ParagraphIdField,
)
from wenyan_models.domain.enums import ReviewStatus, ValidationStatus
from wenyan_models.domain.validation import CheckResult


class ParagraphAssemblyValidationArtifact(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    paragraph_id: ParagraphIdField = Field(alias="paragraphId")
    input_hash: ContentHashField = Field(alias="inputHash")
    status: ValidationStatus
    checks: tuple[CheckResult, ...] = ()


class ParagraphAssemblyReviewArtifact(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    paragraph_id: ParagraphIdField = Field(alias="paragraphId")
    model: str
    input_hash: ContentHashField = Field(alias="inputHash")
    attempts: int
    status: ReviewStatus
    findings: tuple[dict[str, object], ...] = ()
    required_fixes: tuple[dict[str, object], ...] = Field(default=(), alias="requiredFixes")
