from collections.abc import Callable
from typing import Any

from wenyan.jobs.context import JobContext, JobOptions
from wenyan_models.domain.ids import DocumentId, SegmentId
from wenyan_models.domain.results import JobOutcome
from wenyan_models.domain.targets import SegmentTarget

type SegmentJobRunner[T] = Callable[
    [JobContext, DocumentId, SegmentId, JobOptions],
    JobOutcome[T],
]

type SegmentBatchJobRunner[T] = Callable[
    [JobContext, DocumentId, SegmentTarget, JobOptions],
    JobOutcome[T],
]

# Erased variant for registries that hold heterogeneous segment subjob runners.
type SegmentSubjobRunner = SegmentJobRunner[Any]
