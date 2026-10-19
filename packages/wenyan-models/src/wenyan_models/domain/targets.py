from pydantic import BaseModel

from wenyan_models.base import DEFAULT_ARTIFACT_CONFIG
from wenyan_models.domain.ids import ParagraphId, SegmentId


class SingleSegment(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    segment_id: SegmentId


class ParagraphBatch(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    paragraph_id: ParagraphId


SegmentTarget = SingleSegment | ParagraphBatch
