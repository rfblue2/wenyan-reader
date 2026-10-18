from pydantic import ConfigDict

DEFAULT_ARTIFACT_CONFIG = ConfigDict(
    frozen=True,
    populate_by_name=True,
    validate_by_name=True,
    extra="forbid",
)
