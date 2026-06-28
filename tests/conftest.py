from pathlib import Path
import json
import shutil

import pytest

from wenyan.core.adapters.hashing import sha256_text
from wenyan.core.ports.artifact_ref import (
    chapter_proposal_ref,
    chapter_proposal_validation_ref,
    normalized_document_ref,
)
from wenyan.core.ports.artifact_store import ArtifactWrite
from wenyan.jobs.context import JobContext
from wenyan_models.artifacts.normalized import NormalizedDocument
from wenyan_models.artifacts.structure import ChapterProposal, SpanValidationArtifact
from wenyan_models.domain.enums import ValidationStatus
from wenyan_models.domain.ids import DocumentId

REPO_ROOT = Path(__file__).resolve().parents[1]


def install_sunzi_chapter_proposal(ctx: JobContext, document_id: DocumentId) -> ChapterProposal:
    """Install editor-prepared chapter structure for the sunzi-bingfa integration fixture."""
    normalized = ctx.artifacts.read(normalized_document_ref(document_id), NormalizedDocument)
    fixture_path = REPO_ROOT / "tests" / "fixtures" / "preprocess" / "sunzi-bingfa-chapter-proposal.json"
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    payload["documentId"] = str(document_id)
    payload["sourceHash"] = str(normalized.source_hash)
    payload["inputHash"] = str(sha256_text(normalized.normalized_hash))
    chapters = payload["chapters"]
    chapters[-1]["end"] = normalized.character_count
    proposal = ChapterProposal.model_validate(payload)
    validation = SpanValidationArtifact(status=ValidationStatus.PASSED, checks=())
    ctx.artifacts.write_batch(
        [
            ArtifactWrite(ref=chapter_proposal_ref(document_id), payload=proposal),
            ArtifactWrite(
                ref=chapter_proposal_validation_ref(document_id),
                payload=validation,
            ),
        ],
        dry_run=False,
    )
    return proposal


@pytest.fixture
def tmp_workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.delenv("WENYAN_MODEL_PROVIDER", raising=False)
    monkeypatch.delenv("WENYAN_MODEL", raising=False)
    monkeypatch.delenv("MINIMAX_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    workspace = tmp_path / "repo"
    shutil.copytree(REPO_ROOT / "sources", workspace / "sources")
    if (REPO_ROOT / "prompts").is_dir():
        shutil.copytree(REPO_ROOT / "prompts", workspace / "prompts")
    fixtures_src = REPO_ROOT / "tests" / "fixtures"
    if fixtures_src.is_dir():
        shutil.copytree(fixtures_src, workspace / "tests" / "fixtures")
    (workspace / "config").mkdir()
    shutil.copy(REPO_ROOT / "config/preprocessing.yaml", workspace / "config/preprocessing.yaml")
    (workspace / "preprocess").mkdir()
    (workspace / "content").mkdir()
    return workspace
