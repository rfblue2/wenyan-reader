from typing import Literal

from pydantic import BaseModel, ConfigDict


class CommandSuccess(BaseModel):
    model_config = ConfigDict(frozen=True, populate_by_name=True, extra="forbid")

    kind: Literal["success"] = "success"
    output: str


class CommandFailure(BaseModel):
    model_config = ConfigDict(frozen=True, populate_by_name=True, extra="forbid")

    kind: Literal["failure"] = "failure"
    exit_code: int
    message: str


CommandResult = CommandSuccess | CommandFailure


def command_exit_code(result: CommandResult) -> int:
    match result:
        case CommandSuccess():
            return 0
        case CommandFailure(exit_code=code):
            return code
