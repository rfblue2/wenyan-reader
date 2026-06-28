from pydantic import BaseModel, Field

from wenyan_models.artifacts.base import DEFAULT_ARTIFACT_CONFIG
from wenyan_models.artifacts.segment import GlossEntry


class GlossaryDraft(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    glosses: tuple[GlossEntry, ...] = ()
