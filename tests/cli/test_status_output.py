from pathlib import Path

import pytest

from wenyan.bootstrap import build_job_context
from wenyan.cli.status_output import StatusDisplayContext, render_status
from wenyan.cli.status_scope import resolve_status_scope
from wenyan.core.adapters.filesystem_status_reader import FilesystemStatusReader
from wenyan.jobs.context import JobOptions
from wenyan.jobs.ingest_document import run_ingest_document
from wenyan.jobs.split_paragraphs import run_split_paragraphs
from wenyan.jobs.split_segments import run_split_segments
from conftest import install_sunzi_chapter_proposal


def test_render_document_status_lists_chapters(tmp_workspace: Path) -> None:
    ctx = build_job_context(tmp_workspace)
    source_dir = tmp_workspace / "sources" / "documents" / "sunzi-bingfa"
    doc_id = run_ingest_document(ctx, source_dir, JobOptions()).artifact  # type: ignore[union-attr]
    install_sunzi_chapter_proposal(ctx, doc_id)
    reader = FilesystemStatusReader(ctx.artifacts, tmp_workspace)
    output = render_status(
        reader.document_status(doc_id),
        StatusDisplayContext(),
    )
    assert "Chapters" in output
    assert "始計第一" in output
    assert "#1" in output


def test_render_chapter_status_lists_paragraphs(tmp_workspace: Path) -> None:
    ctx = build_job_context(tmp_workspace)
    source_dir = tmp_workspace / "sources" / "documents" / "sunzi-bingfa"
    doc_id = run_ingest_document(ctx, source_dir, JobOptions()).artifact  # type: ignore[union-attr]
    chapter_proposal = install_sunzi_chapter_proposal(ctx, doc_id)
    chapter_id_value = chapter_proposal.chapters[0].id
    run_split_paragraphs(ctx, doc_id, chapter_id_value, JobOptions())
    reader = FilesystemStatusReader(ctx.artifacts, tmp_workspace)
    output = render_status(
        reader.chapter_status(doc_id, chapter_id_value),
        StatusDisplayContext(chapter_handle="1"),
    )
    assert "Paragraphs" in output
    assert "#1" in output


def test_resolve_chapter_by_number_and_title(tmp_workspace: Path) -> None:
    ctx = build_job_context(tmp_workspace)
    source_dir = tmp_workspace / "sources" / "documents" / "sunzi-bingfa"
    doc_id = run_ingest_document(ctx, source_dir, JobOptions()).artifact  # type: ignore[union-attr]
    install_sunzi_chapter_proposal(ctx, doc_id)
    by_number = resolve_status_scope(
        ctx.artifacts,
        doc_id,
        "sunzi-bingfa",
        chapter="1",
        paragraph=None,
        segment=None,
    )
    by_title = resolve_status_scope(
        ctx.artifacts,
        doc_id,
        "sunzi-bingfa",
        chapter="始計第一",
        paragraph=None,
        segment=None,
    )
    assert by_number.level == "chapter"
    assert by_title.chapter_id == by_number.chapter_id
    assert by_number.chapter_handle == "1"
    assert by_title.chapter_handle == "始計第一"


def test_resolve_paragraph_and_segment_by_number(tmp_workspace: Path) -> None:
    ctx = build_job_context(tmp_workspace)
    source_dir = tmp_workspace / "sources" / "documents" / "sunzi-bingfa"
    doc_id = run_ingest_document(ctx, source_dir, JobOptions()).artifact  # type: ignore[union-attr]
    chapter_proposal = install_sunzi_chapter_proposal(ctx, doc_id)
    chapter_id_value = chapter_proposal.chapters[0].id
    paragraphs = run_split_paragraphs(ctx, doc_id, chapter_id_value, JobOptions()).artifact  # type: ignore[union-attr]
    paragraph_id_value = paragraphs.paragraphs[0].id
    run_split_segments(ctx, doc_id, paragraph_id_value, JobOptions())
    scope = resolve_status_scope(
        ctx.artifacts,
        doc_id,
        "sunzi-bingfa",
        chapter="1",
        paragraph="1",
        segment="1",
    )
    assert scope.level == "segment"
    assert scope.chapter_handle == "1"
    assert scope.paragraph_handle == "1"
    assert scope.segment_handle == "1"


def test_render_paragraph_status_shows_assembly_section(tmp_workspace: Path) -> None:
    from tests.jobs.assembly_helpers import prepare_paragraph_with_complete_segments

    ctx, doc_id, paragraph_id_value = prepare_paragraph_with_complete_segments(tmp_workspace)
    reader = FilesystemStatusReader(ctx.artifacts, tmp_workspace)
    output = render_status(
        reader.paragraph_status(doc_id, paragraph_id_value),
        StatusDisplayContext(chapter_handle="1", paragraph_handle="1"),
    )
    assert "Assembly" in output
    assert "assemble-paragraph" in output
    assert "review-paragraph-assembly" in output


def test_paragraph_number_requires_chapter(tmp_workspace: Path) -> None:
    ctx = build_job_context(tmp_workspace)
    source_dir = tmp_workspace / "sources" / "documents" / "sunzi-bingfa"
    doc_id = run_ingest_document(ctx, source_dir, JobOptions()).artifact  # type: ignore[union-attr]
    install_sunzi_chapter_proposal(ctx, doc_id)
    with pytest.raises(ValueError, match="requires --chapter"):
        resolve_status_scope(
            ctx.artifacts,
            doc_id,
            "sunzi-bingfa",
            chapter=None,
            paragraph="1",
            segment=None,
        )
