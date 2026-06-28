from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")

_DEFAULT_MODEL_CONFIG = ConfigDict(frozen=True, populate_by_name=True, extra="forbid")


class Skipped(BaseModel):
    model_config = _DEFAULT_MODEL_CONFIG

    kind: Literal["skipped"] = "skipped"
    reason: str


class Promoted(BaseModel, Generic[T]):
    model_config = _DEFAULT_MODEL_CONFIG

    kind: Literal["promoted"] = "promoted"
    artifact: T


class JobFailure(BaseModel):
    model_config = _DEFAULT_MODEL_CONFIG

    kind: Literal["failure"] = "failure"
    code: str
    message: str


type JobOutcome[T] = Promoted[T] | Skipped | JobFailure


def outcome_exit_code[T](outcome: Promoted[T] | Skipped | JobFailure) -> int:
    match outcome:
        case Promoted() | Skipped():
            return 0
        case JobFailure():
            return 1
