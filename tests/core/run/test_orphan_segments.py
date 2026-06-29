from pathlib import Path

from wenyan.bootstrap import build_job_context
from wenyan.core.adapters.paths import document_root
from wenyan.core.ports.artifact_ref import paragraph_draft_ref
from wenyan.core.run.orphan_segments import find_orphan_segments, prune_orphan_segments
from wenyan.jobs.context import JobOptions
from wenyan.jobs.ingest_document import run_ingest_document
from wenyan.jobs.prune_orphan_segments import run_prune_orphan_segments
from wenyan.jobs.split_paragraphs import run_split_paragraphs
from wenyan.jobs.split_segments import run_split_segments
from wenyan_models.artifacts.paragraph import ParagraphDraft
from wenyan_models.domain.results import Promoted, Skipped
from conftest import install_sunzi_chapter_proposal


def _prepare_paragraph_with_segments(tmp_workspace: Path):
    ctx = build_job_context(tmp_workspace)
    source_dir = tmp_workspace / "sources" / "documents" / "sunzi-bingfa"
    doc_id = run_ingest_document(ctx, source_dir, JobOptions()).artifact  # type: ignore[union-attr]
    chapter_proposal = install_sunzi_chapter_proposal(ctx, doc_id)
    chapter_id_value = chapter_proposal.chapters[0].id
    paragraphs = run_split_paragraphs(ctx, doc_id, chapter_id_value, JobOptions()).artifact  # type: ignore[union-attr]
    paragraph_id_value = paragraphs.paragraphs[0].id
    draft = run_split_segments(ctx, doc_id, paragraph_id_value, JobOptions()).artifact  # type: ignore[union-attr]
    return ctx, doc_id, paragraph_id_value, draft


def test_find_orphan_segments_after_resplit(tmp_workspace: Path) -> None:
    ctx, doc_id, paragraph_id_value, first_draft = _prepare_paragraph_with_segments(tmp_workspace)
    first_segment_ids = {segment.id for segment in first_draft.segments}

    run_split_segments(ctx, doc_id, paragraph_id_value, JobOptions(force=True))

    orphans = find_orphan_segments(ctx.artifacts, tmp_workspace, doc_id)
    orphan_ids = {item.segment_id for item in orphans}
    assert orphan_ids == first_segment_ids

    current_draft = ctx.artifacts.read(paragraph_draft_ref(doc_id, paragraph_id_value), ParagraphDraft)
    current_segment_ids = {segment.id for segment in current_draft.segments}
    assert orphan_ids.isdisjoint(current_segment_ids)


def test_prune_orphan_segments_dry_run_leaves_files(tmp_workspace: Path) -> None:
    ctx, doc_id, paragraph_id_value, first_draft = _prepare_paragraph_with_segments(tmp_workspace)
    first_segment_id = first_draft.segments[0].id

    run_split_segments(ctx, doc_id, paragraph_id_value, JobOptions(force=True))

    outcome = run_prune_orphan_segments(ctx, doc_id, JobOptions(dry_run=True))
    assert isinstance(outcome, Promoted)
    assert outcome.artifact.dry_run is True
    assert first_segment_id in {item.segment_id for item in outcome.artifact.removed}
    assert (document_root(tmp_workspace, doc_id) / "jobs" / "segments" / str(first_segment_id)).is_dir()


def test_prune_orphan_segments_removes_stale_directories(tmp_workspace: Path) -> None:
    ctx, doc_id, paragraph_id_value, first_draft = _prepare_paragraph_with_segments(tmp_workspace)
    stale_segment_ids = {segment.id for segment in first_draft.segments}

    run_split_segments(ctx, doc_id, paragraph_id_value, JobOptions(force=True))

    outcome = run_prune_orphan_segments(ctx, doc_id, JobOptions())
    assert isinstance(outcome, Promoted)
    segments_root = document_root(tmp_workspace, doc_id) / "jobs" / "segments"
    for segment_id_value in stale_segment_ids:
        assert not (segments_root / str(segment_id_value)).exists()
    assert find_orphan_segments(ctx.artifacts, tmp_workspace, doc_id) == ()


def test_prune_orphan_segments_skips_when_none(tmp_workspace: Path) -> None:
    ctx, doc_id, _, _ = _prepare_paragraph_with_segments(tmp_workspace)

    outcome = run_prune_orphan_segments(ctx, doc_id, JobOptions())
    assert isinstance(outcome, Skipped)
    assert outcome.reason == "no orphaned segments"


def test_prune_orphan_segments_core_dry_run(tmp_workspace: Path) -> None:
    ctx, doc_id, paragraph_id_value, _ = _prepare_paragraph_with_segments(tmp_workspace)
    run_split_segments(ctx, doc_id, paragraph_id_value, JobOptions(force=True))

    result = prune_orphan_segments(ctx.artifacts, tmp_workspace, doc_id, dry_run=True)
    assert result.dry_run is True
    assert result.removed
    assert find_orphan_segments(ctx.artifacts, tmp_workspace, doc_id)
