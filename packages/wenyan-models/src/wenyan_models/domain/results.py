from typing import Literal

from pydantic import BaseModel

from wenyan_models.base import DEFAULT_ARTIFACT_CONFIG


class Skipped(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    kind: Literal["skipped"] = "skipped"
    reason: str


class Promoted[T](BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    kind: Literal["promoted"] = "promoted"
    artifact: T


class JobFailure(BaseModel):
    model_config = DEFAULT_ARTIFACT_CONFIG

    kind: Literal["failure"] = "failure"
    code: str
    message: str


type JobOutcome[T] = Promoted[T] | Skipped | JobFailure


def outcome_exit_code[T](outcome: JobOutcome[T]) -> int:
    match outcome:
        case Promoted() | Skipped():
            return 0
        case JobFailure():
            return 1
