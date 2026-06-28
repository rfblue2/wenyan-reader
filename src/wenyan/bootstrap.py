from collections.abc import Sequence
from pathlib import Path

from pydantic import BaseModel

from wenyan.core.adapters.filesystem_artifact_store import FilesystemArtifactStore
from wenyan.core.config.loader import load_preprocessing_config
from wenyan.core.ports.llm_client import LLMClient, StructuredPrompt
from wenyan.core.ports.source_registry import SourceRegistry
from wenyan.core.ports.span_validator import SpanValidator
from wenyan.jobs.context import JobContext
from wenyan_models.domain.ids import DocumentId, Slug
from wenyan_models.domain.spans import ChapterSpan, ParagraphSpan, SegmentShell
from wenyan_models.domain.validation import SpanValidationResult
from wenyan_models.sources import DocumentYaml, RegistryEntry


class _StubRegistry(SourceRegistry):
    def resolve(self, id_or_slug: str) -> RegistryEntry:
        raise NotImplementedError

    def assign_document_id(self, slug: Slug, document_id: DocumentId) -> None:
        raise NotImplementedError

    def load_document_yaml(self, slug: Slug) -> DocumentYaml:
        raise NotImplementedError


class _StubLLM(LLMClient):
    def complete_model[T: BaseModel](
        self,
        prompt: StructuredPrompt,
        model: type[T],
    ) -> T:
        raise NotImplementedError


class _StubSpanValidator(SpanValidator):
    def validate_chapters(
        self,
        text: str,
        chapters: Sequence[ChapterSpan],
    ) -> SpanValidationResult:
        raise NotImplementedError

    def validate_paragraphs(
        self,
        text: str,
        paragraphs: Sequence[ParagraphSpan],
    ) -> SpanValidationResult:
        raise NotImplementedError

    def validate_segments(
        self,
        text: str,
        segments: Sequence[SegmentShell],
    ) -> SpanValidationResult:
        raise NotImplementedError


def build_job_context(repo_root: Path) -> JobContext:
    config = load_preprocessing_config(repo_root)
    return JobContext(
        repo_root=repo_root,
        config=config,
        artifacts=FilesystemArtifactStore(repo_root),
        registry=_StubRegistry(),
        llm=_StubLLM(),
        spans=_StubSpanValidator(),
    )
