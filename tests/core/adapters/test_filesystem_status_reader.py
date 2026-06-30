import json
from pathlib import Path

import pytest

from wenyan.bootstrap import build_job_context
from wenyan.core.adapters.filesystem_status_reader import FilesystemStatusReader
from wenyan.jobs.context import JobOptions
from wenyan.jobs.gloss_segment import run_gloss_segment
from wenyan.jobs.ingest_document import run_ingest_document
from wenyan.jobs.review_segment_gloss import run_review_segment_gloss
from wenyan.jobs.review_segment_tokenization import run_review_segment_tokenization
from wenyan.jobs.split_paragraphs import run_split_paragraphs
from wenyan.jobs.split_segments import run_split_segments
from wenyan.jobs.tokenize_segment import run_tokenize_segment
from wenyan_models.domain.enums import UnitStatus
from wenyan_models.domain.targets import single_segment_target
from conftest import install_sunzi_chapter_proposal


def _prepare_sunzi_first_segment(tmp_workspace: Path):
    ctx = build_job_context(tmp_workspace)
    source_dir = tmp_workspace / "sources" / "documents" / "sunzi-bingfa"
    doc_id = run_ingest_document(ctx, source_dir, JobOptions()).artifact  # type: ignore[union-attr]
    chapter_proposal = install_sunzi_chapter_proposal(ctx, doc_id)
    chapter_id_value = chapter_proposal.chapters[0].id
    paragraphs = run_split_paragraphs(ctx, doc_id, chapter_id_value, JobOptions()).artifact  # type: ignore[union-attr]
    paragraph_id_value = paragraphs.paragraphs[0].id
    draft = run_split_segments(ctx, doc_id, paragraph_id_value, JobOptions()).artifact  # type: ignore[union-attr]
    segment_id_value = draft.segments[0].id
    run_tokenize_segment(ctx, doc_id, single_segment_target(segment_id_value), JobOptions())
    run_review_segment_tokenization(ctx, doc_id, segment_id_value, JobOptions())
    run_gloss_segment(ctx, doc_id, single_segment_target(segment_id_value), JobOptions())
    run_review_segment_gloss(ctx, doc_id, segment_id_value, JobOptions())
    return ctx, doc_id, chapter_id_value, paragraph_id_value, segment_id_value


def test_document_status_lists_chapters(tmp_workspace: Path) -> None:
    ctx, doc_id, chapter_id_value, _, _ = _prepare_sunzi_first_segment(tmp_workspace)
    reader = FilesystemStatusReader(ctx.artifacts, tmp_workspace)
    payload = reader.document_status(doc_id)
    assert payload.scope.type == "document"
    assert payload.counts.chapters == len(payload.chapters)
    first_chapter = next(item for item in payload.chapters if item.chapter_id == str(chapter_id_value))
    assert first_chapter.status == UnitStatus.IN_PROGRESS
    assert first_chapter.progress is not None
    assert first_chapter.progress.paragraphs_total is not None


def test_chapter_status_lists_paragraphs(tmp_workspace: Path) -> None:
    ctx, doc_id, chapter_id_value, paragraph_id_value, _ = _prepare_sunzi_first_segment(tmp_workspace)
    reader = FilesystemStatusReader(ctx.artifacts, tmp_workspace)
    payload = reader.chapter_status(doc_id, chapter_id_value)
    assert payload.scope.type == "chapter"
    assert payload.chapter_id == chapter_id_value
    assert payload.counts.paragraphs == len(payload.paragraphs)
    first_paragraph = next(item for item in payload.paragraphs if item.paragraph_id == str(paragraph_id_value))
    assert first_paragraph.ordinal == 1
    assert first_paragraph.status == UnitStatus.IN_PROGRESS
    assert first_paragraph.progress is not None
    assert first_paragraph.progress.segments_total is not None


def test_paragraph_status_lists_segments(tmp_workspace: Path) -> None:
    ctx, doc_id, chapter_id_value, paragraph_id_value, segment_id_value = _prepare_sunzi_first_segment(
        tmp_workspace,
    )
    reader = FilesystemStatusReader(ctx.artifacts, tmp_workspace)
    payload = reader.paragraph_status(doc_id, paragraph_id_value)
    assert payload.scope.type == "paragraph"
    assert payload.chapter_id == chapter_id_value
    assert payload.paragraph_id == paragraph_id_value
    assert payload.structure.status == UnitStatus.COMPLETE
    assert payload.structure.segment_count is not None
    assert payload.counts.segments == len(payload.segments)
    assert payload.assembly is not None
    assert payload.assembly.assemble.status == UnitStatus.PENDING
    first_segment = next(item for item in payload.segments if item.segment_id == str(segment_id_value))
    assert first_segment.ordinal == 1
    assert first_segment.text_preview
    assert first_segment.progress is not None
    assert first_segment.progress.components_total == 8


def test_paragraph_status_in_progress_when_all_segments_complete(tmp_workspace: Path) -> None:
    from tests.jobs.assembly_helpers import prepare_paragraph_with_complete_segments

    ctx, doc_id, paragraph_id_value = prepare_paragraph_with_complete_segments(tmp_workspace)
    reader = FilesystemStatusReader(ctx.artifacts, tmp_workspace)
    payload = reader.paragraph_status(doc_id, paragraph_id_value)
    chapter_payload = reader.chapter_status(doc_id, payload.chapter_id)
    paragraph_item = next(item for item in chapter_payload.paragraphs if item.paragraph_id == str(paragraph_id_value))

    assert payload.counts.complete == payload.counts.segments
    assert payload.assembly is not None
    assert payload.assembly.assemble.status == UnitStatus.PENDING
    assert paragraph_item.status == UnitStatus.IN_PROGRESS


def test_segment_status_lists_components(tmp_workspace: Path) -> None:
    ctx, doc_id, chapter_id_value, paragraph_id_value, segment_id_value = _prepare_sunzi_first_segment(
        tmp_workspace,
    )
    reader = FilesystemStatusReader(ctx.artifacts, tmp_workspace)
    payload = reader.segment_status(doc_id, segment_id_value)
    assert payload.scope.type == "segment"
    assert payload.chapter_id == chapter_id_value
    assert payload.paragraph_id == paragraph_id_value
    assert payload.segment_id == segment_id_value
    assert payload.text
    assert payload.status == UnitStatus.IN_PROGRESS
    assert len(payload.components) == 8
    completed = [component for component in payload.components if component.status == UnitStatus.COMPLETE]
    assert len(completed) == 4
    pending = [component for component in payload.components if component.status == UnitStatus.PENDING]
    assert len(pending) == 4


def test_status_json_matches_schema(tmp_workspace: Path) -> None:
    ctx, doc_id, _, _, segment_id_value = _prepare_sunzi_first_segment(tmp_workspace)
    reader = FilesystemStatusReader(ctx.artifacts, tmp_workspace)
    payload = reader.segment_status(doc_id, segment_id_value)
    data = json.loads(payload.model_dump_json(by_alias=True))
    assert data["scope"]["type"] == "segment"
    assert data["components"][0]["kind"] == "tokenize-segment"


def test_paragraph_status_missing_raises(tmp_workspace: Path) -> None:
    ctx, doc_id, _, _, _ = _prepare_sunzi_first_segment(tmp_workspace)
    reader = FilesystemStatusReader(ctx.artifacts, tmp_workspace)
    from wenyan_models.domain.ids import paragraph_id

    with pytest.raises(ValueError, match="paragraph"):
        reader.paragraph_status(doc_id, paragraph_id("00000000-0000-0000-0000-000000000099"))
