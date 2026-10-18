from pathlib import Path

import pytest
from typer.testing import CliRunner

from wenyan.bootstrap import build_job_context
from wenyan.cli import app
from wenyan.core.ports.artifact_ref import SegmentArtifactKind, SegmentRef
from wenyan.jobs.context import JobOptions
from wenyan.jobs.ingest_document import run_ingest_document
from wenyan.jobs.split_paragraphs import run_split_paragraphs
from wenyan.jobs.split_segments import run_split_segments
from conftest import install_sunzi_chapter_proposal


def test_review_command_over_paragraph_reviews_every_segment(
    tmp_workspace: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ctx = build_job_context(tmp_workspace)
    source_dir = tmp_workspace / "sources" / "documents" / "sunzi-bingfa"
    doc_id = run_ingest_document(ctx, source_dir, JobOptions()).artifact  # type: ignore[union-attr]
    chapter_id_value = install_sunzi_chapter_proposal(ctx, doc_id).chapters[0].id
    paragraphs = run_split_paragraphs(ctx, doc_id, chapter_id_value, JobOptions()).artifact  # type: ignore[union-attr]
    for ordinal, paragraph in enumerate(paragraphs.paragraphs, start=1):
        draft = run_split_segments(ctx, doc_id, paragraph.id, JobOptions()).artifact  # type: ignore[union-attr]
        if len(draft.segments) > 1:
            break
    assert len(draft.segments) > 1

    monkeypatch.chdir(tmp_workspace)
    scope = ["sunzi-bingfa", "--chapter", "1", "--paragraph", str(ordinal)]
    for command in ("tokenize-segment", "review-segment-tokenization"):
        result = CliRunner().invoke(app, ["preprocess", command, *scope])
        assert result.exit_code == 0, result.stdout

    for segment in draft.segments:
        review_ref = SegmentRef(SegmentArtifactKind.TOKENIZATION_REVIEW, doc_id, segment.id)
        assert ctx.artifacts.exists(review_ref)
