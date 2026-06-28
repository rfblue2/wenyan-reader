from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from wenyan.core.ports.artifact_store import ArtifactStore
from wenyan.core.ports.llm_client import LLMClient
from wenyan.core.ports.normalized_text_store import NormalizedTextStore
from wenyan.core.ports.source_registry import SourceRegistry
from wenyan.core.ports.span_validator import SpanValidator
from wenyan_models.config import PreprocessingConfig


class JobOptions(BaseModel):
    model_config = ConfigDict(frozen=True, populate_by_name=True, extra="forbid")

    force: bool = False
    dry_run: bool = False


@dataclass(frozen=True)
class JobContext:
    repo_root: Path
    config: PreprocessingConfig
    artifacts: ArtifactStore
    normalized_text: NormalizedTextStore
    registry: SourceRegistry
    llm: LLMClient
    spans: SpanValidator
