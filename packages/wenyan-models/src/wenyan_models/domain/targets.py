from pydantic import BaseModel, Field

from wenyan_models.artifacts.base import DEFAULT_ARTIFACT_CONFIG
from wenyan_models.domain.ids import ParagraphId, SegmentId


class SingleSegment(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    kind: str = "single-segment"
    segment_id: SegmentId = Field(alias="segmentId")


class ParagraphBatch(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    kind: str = "paragraph-batch"
    paragraph_id: ParagraphId = Field(alias="paragraphId")


SegmentTarget = SingleSegment | ParagraphBatch


def single_segment_target(segment_id_value: SegmentId) -> SingleSegment:
    return SingleSegment.model_validate(
        {"kind": "single-segment", "segmentId": str(segment_id_value)},
    )


def paragraph_batch_target(paragraph_id_value: ParagraphId) -> ParagraphBatch:
    return ParagraphBatch.model_validate(
        {"kind": "paragraph-batch", "paragraphId": str(paragraph_id_value)},
    )
