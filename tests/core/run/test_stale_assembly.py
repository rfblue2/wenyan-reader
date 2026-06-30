from pathlib import Path

from wenyan.core.adapters.paths import document_root
from wenyan.core.ports.artifact_ref import paragraph_draft_ref
from wenyan.core.run.stale_assembly import (
    find_stale_assembly_paragraphs,
    prune_stale_assembly,
)
from wenyan.jobs.assemble_paragraph import run_assemble_paragraph
from wenyan.jobs.context import JobOptions
from wenyan.jobs.prune_orphan_segments import run_prune_orphan_segments
from wenyan.jobs.split_segments import run_split_segments
from wenyan_models.artifacts.paragraph import ParagraphDraft
from wenyan_models.domain.results import Promoted
from tests.jobs.assembly_helpers import prepare_paragraph_with_complete_segments


def test_find_stale_assembly_after_segment_artifact_deleted(tmp_workspace: Path) -> None:
    ctx, doc_id, paragraph_id_value = prepare_paragraph_with_complete_segments(tmp_workspace)
    run_assemble_paragraph(ctx, doc_id, paragraph_id_value, JobOptions())

    assembly_dir = document_root(tmp_workspace, doc_id) / "jobs" / "assembly" / str(paragraph_id_value)
    assert assembly_dir.is_dir()
    assert find_stale_assembly_paragraphs(ctx.artifacts, tmp_workspace, doc_id) == ()

    draft = ctx.artifacts.read(paragraph_draft_ref(doc_id, paragraph_id_value), ParagraphDraft)
    glosses_path = document_root(tmp_workspace, doc_id) / "jobs" / "segments" / str(
        draft.segments[0].id
    ) / "glosses.json"
    glosses_path.unlink()

    stale = find_stale_assembly_paragraphs(ctx.artifacts, tmp_workspace, doc_id)
    assert stale == (paragraph_id_value,)


def test_prune_stale_assembly_removes_assembly_dir(tmp_workspace: Path) -> None:
    ctx, doc_id, paragraph_id_value = prepare_paragraph_with_complete_segments(tmp_workspace)
    run_assemble_paragraph(ctx, doc_id, paragraph_id_value, JobOptions())

    assembly_dir = document_root(tmp_workspace, doc_id) / "jobs" / "assembly" / str(paragraph_id_value)
    draft = ctx.artifacts.read(paragraph_draft_ref(doc_id, paragraph_id_value), ParagraphDraft)
    glosses_path = document_root(tmp_workspace, doc_id) / "jobs" / "segments" / str(
        draft.segments[0].id
    ) / "glosses.json"
    glosses_path.unlink()

    removed = prune_stale_assembly(ctx.artifacts, tmp_workspace, doc_id, dry_run=False)
    assert assembly_dir.relative_to(tmp_workspace).as_posix() in removed
    assert not assembly_dir.exists()
    assert find_stale_assembly_paragraphs(ctx.artifacts, tmp_workspace, doc_id) == ()


def test_prune_stale_assembly_dry_run_leaves_files(tmp_workspace: Path) -> None:
    ctx, doc_id, paragraph_id_value = prepare_paragraph_with_complete_segments(tmp_workspace)
    run_assemble_paragraph(ctx, doc_id, paragraph_id_value, JobOptions())

    assembly_dir = document_root(tmp_workspace, doc_id) / "jobs" / "assembly" / str(paragraph_id_value)
    draft = ctx.artifacts.read(paragraph_draft_ref(doc_id, paragraph_id_value), ParagraphDraft)
    glosses_path = document_root(tmp_workspace, doc_id) / "jobs" / "segments" / str(
        draft.segments[0].id
    ) / "glosses.json"
    glosses_path.unlink()

    removed = prune_stale_assembly(ctx.artifacts, tmp_workspace, doc_id, dry_run=True)
    assert removed
    assert assembly_dir.is_dir()


def test_prune_orphan_segments_also_prunes_stale_assembly(tmp_workspace: Path) -> None:
    ctx, doc_id, paragraph_id_value = prepare_paragraph_with_complete_segments(tmp_workspace)
    run_assemble_paragraph(ctx, doc_id, paragraph_id_value, JobOptions())

    assembly_dir = document_root(tmp_workspace, doc_id) / "jobs" / "assembly" / str(paragraph_id_value)
    assert assembly_dir.is_dir()

    run_split_segments(ctx, doc_id, paragraph_id_value, JobOptions(force=True))

    outcome = run_prune_orphan_segments(ctx, doc_id, JobOptions())
    assert isinstance(outcome, Promoted)
    assert not assembly_dir.exists()
