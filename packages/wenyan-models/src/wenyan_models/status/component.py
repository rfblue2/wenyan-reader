from pydantic import BaseModel, Field

from wenyan_models.base import DEFAULT_ARTIFACT_CONFIG
from wenyan_models.domain.enums import ComponentKind, UnitStatus
from wenyan_models.domain.review import ReviewFinding


class ComponentStatusItem(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    kind: ComponentKind
    status: UnitStatus
    artifact_path: str | None = Field(default=None, alias="artifactPath")
    attempts: int | None = None
    blocked_reason: str | None = Field(default=None, alias="blockedReason")
    required_fixes: tuple[ReviewFinding, ...] = Field(default=(), alias="requiredFixes")
