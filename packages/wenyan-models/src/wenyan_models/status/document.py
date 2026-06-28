from pydantic import BaseModel, ConfigDict

from wenyan_models.domain.enums import UnitStatus
from wenyan_models.domain.ids import DocumentId

_DEFAULT_MODEL_CONFIG = ConfigDict(frozen=True, populate_by_name=True, extra="forbid")


class DocumentStatus(BaseModel):
    model_config = _DEFAULT_MODEL_CONFIG

    document_id: DocumentId
    status: UnitStatus
