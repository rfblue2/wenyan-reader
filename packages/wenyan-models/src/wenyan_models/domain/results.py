from typing import Annotated, Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field

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


JobOutcome = Annotated[
    Promoted[T] | Skipped | JobFailure,
    Field(discriminator="kind"),
]


def outcome_exit_code(outcome: Promoted[object] | Skipped | JobFailure) -> int:
    match outcome:
        case Promoted() | Skipped():
            return 0
        case JobFailure():
            return 1
