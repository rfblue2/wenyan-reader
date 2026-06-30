from pydantic import BaseModel, Field

from wenyan_models.artifacts.base import DEFAULT_ARTIFACT_CONFIG, ContentHashField
from wenyan_models.domain.enums import ValidationStatus
from wenyan_models.domain.validation import CheckResult


class PackageValidationArtifact(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    input_hash: ContentHashField = Field(alias="inputHash")
    status: ValidationStatus
    checks: tuple[CheckResult, ...] = ()
    paragraphs_packaged: int = Field(alias="paragraphsPackaged")
