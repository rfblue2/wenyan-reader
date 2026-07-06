from pydantic import BaseModel, ConfigDict, Field

_REVIEW_MODEL_CONFIG = ConfigDict(
    frozen=True,
    populate_by_name=True,
    validate_by_name=True,
    extra="ignore",
)


class ReviewFindingTarget(BaseModel):
    model_config = _REVIEW_MODEL_CONFIG

    token_id: str | None = Field(default=None, alias="tokenId")
    note_id: str | None = Field(default=None, alias="noteId")


class ReviewFinding(BaseModel):
    model_config = _REVIEW_MODEL_CONFIG

    severity: str = "error"
    message: str = ""
    token_id: str | None = Field(default=None, alias="tokenId")
    note_id: str | None = Field(default=None, alias="noteId")
    surface: str | None = None
    problem: str | None = None
    detail: str | None = None
    reason: str | None = None
    finding: str | None = None
    target: ReviewFindingTarget | None = None

    def display_line(self) -> str:
        prefix_parts: list[str] = []
        surface = self.surface
        if surface:
            prefix_parts.append(surface)

        note_id = self.note_id or (self.target.note_id if self.target else None)
        if note_id:
            prefix_parts.append(f"note {note_id[:8]}…")

        token_id = self.token_id or (self.target.token_id if self.target else None)
        if token_id and not prefix_parts:
            prefix_parts.append(f"token {token_id[:8]}…")

        text_parts: list[str] = []
        seen: set[str] = set()
        for value in (self.message, self.reason, self.finding, self.problem, self.detail):
            if value and value not in seen:
                text_parts.append(value)
                seen.add(value)

        if prefix_parts and text_parts:
            return f"{prefix_parts[0]} — {text_parts[0]}" + (
                f" — {text_parts[1]}" if len(text_parts) > 1 else ""
            )
        if text_parts:
            return " — ".join(text_parts)
        if prefix_parts:
            return prefix_parts[0]
        return self.model_dump_json(by_alias=True)
