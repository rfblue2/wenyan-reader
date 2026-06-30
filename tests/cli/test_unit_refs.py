from pathlib import Path

import pytest
import typer

from wenyan.bootstrap import build_job_context
from wenyan.cli.unit_refs import segment_or_paragraph_batch_target
from wenyan.jobs.context import JobOptions
from wenyan.jobs.ingest_document import run_ingest_document
from wenyan.jobs.split_paragraphs import run_split_paragraphs
from wenyan.jobs.split_segments import run_split_segments
from wenyan_models.domain.targets import SingleSegment
from conftest import install_sunzi_chapter_proposal


def test_segment_target_with_ordinal_context(tmp_workspace: Path) -> None:
    ctx = build_job_context(tmp_workspace)
    source_dir = tmp_workspace / "sources" / "documents" / "sunzi-bingfa"
    doc_id = run_ingest_document(ctx, source_dir, JobOptions()).artifact  # type: ignore[union-attr]
    chapter_proposal = install_sunzi_chapter_proposal(ctx, doc_id)
    chapter_id_value = chapter_proposal.chapters[0].id
    paragraphs = run_split_paragraphs(ctx, doc_id, chapter_id_value, JobOptions()).artifact  # type: ignore[union-attr]
    paragraph_id_value = paragraphs.paragraphs[0].id
    segments = run_split_segments(ctx, doc_id, paragraph_id_value, JobOptions()).artifact  # type: ignore[union-attr]
    expected_segment_id = segments.segments[0].id

    target = segment_or_paragraph_batch_target(
        ctx,
        doc_id,
        segment="1",
        paragraph="1",
        chapter="1",
    )
    assert isinstance(target, SingleSegment)
    assert target.segment_id == expected_segment_id


def test_segment_target_requires_paragraph_or_chapter_context(tmp_workspace: Path) -> None:
    ctx = build_job_context(tmp_workspace)
    source_dir = tmp_workspace / "sources" / "documents" / "sunzi-bingfa"
    doc_id = run_ingest_document(ctx, source_dir, JobOptions()).artifact  # type: ignore[union-attr]
    install_sunzi_chapter_proposal(ctx, doc_id)

    with pytest.raises(typer.BadParameter, match="requires --paragraph"):
        segment_or_paragraph_batch_target(
            ctx,
            doc_id,
            segment="1",
            paragraph=None,
            chapter=None,
        )


def test_segment_or_paragraph_batch_requires_target(tmp_workspace: Path) -> None:
    ctx = build_job_context(tmp_workspace)
    source_dir = tmp_workspace / "sources" / "documents" / "sunzi-bingfa"
    doc_id = run_ingest_document(ctx, source_dir, JobOptions()).artifact  # type: ignore[union-attr]

    with pytest.raises(typer.BadParameter, match="provide --segment or --paragraph"):
        segment_or_paragraph_batch_target(
            ctx,
            doc_id,
            segment=None,
            paragraph=None,
            chapter=None,
        )


def test_validate_artifacts_accepts_ordinal_segment(
    tmp_workspace: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from typer.testing import CliRunner

    from wenyan.cli import app

    ctx = build_job_context(tmp_workspace)
    source_dir = tmp_workspace / "sources" / "documents" / "sunzi-bingfa"
    doc_id = run_ingest_document(ctx, source_dir, JobOptions()).artifact  # type: ignore[union-attr]
    chapter_proposal = install_sunzi_chapter_proposal(ctx, doc_id)
    chapter_id_value = chapter_proposal.chapters[0].id
    paragraphs = run_split_paragraphs(ctx, doc_id, chapter_id_value, JobOptions()).artifact  # type: ignore[union-attr]
    run_split_segments(ctx, doc_id, paragraphs.paragraphs[0].id, JobOptions())

    monkeypatch.chdir(tmp_workspace)
    result = CliRunner().invoke(
        app,
        [
            "preprocess",
            "validate-artifacts",
            "sunzi-bingfa",
            "--chapter",
            "1",
            "--paragraph",
            "1",
            "--segment",
            "1",
        ],
    )
    assert result.exit_code == 0
    assert result.stdout.strip() == "ok"
