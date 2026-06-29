from pathlib import Path

from wenyan.bootstrap import build_job_context
from wenyan.core.run.work_queue import find_next_paragraph_needing_split_segments, find_next_segment_work
from wenyan.jobs.run_preprocess import run_preprocess
from wenyan.jobs.context import JobOptions
from conftest import install_sunzi_chapter_proposal


def test_find_next_paragraph_without_draft(tmp_workspace: Path) -> None:
    ctx = build_job_context(tmp_workspace)
    from wenyan.jobs.ingest_document import run_ingest_document

    source_dir = tmp_workspace / "sources" / "documents" / "sunzi-bingfa"
    outcome = run_ingest_document(ctx, source_dir, JobOptions())
    doc_id = outcome.artifact  # type: ignore[union-attr]
    chapter_proposal = install_sunzi_chapter_proposal(ctx, doc_id)
    chapter_id_value = chapter_proposal.chapters[0].id

    from wenyan.jobs.split_paragraphs import run_split_paragraphs

    paragraphs_outcome = run_split_paragraphs(ctx, doc_id, chapter_id_value, JobOptions())
    paragraph_id_value = paragraphs_outcome.artifact.paragraphs[0].id  # type: ignore[union-attr]

    work = find_next_paragraph_needing_split_segments(ctx.artifacts, doc_id)
    assert work is not None
    assert work.paragraph_id == paragraph_id_value


def test_find_next_segment_stays_on_incomplete_segment(tmp_workspace: Path) -> None:
    ctx = build_job_context(tmp_workspace)
    from wenyan.jobs.ingest_document import run_ingest_document
    from wenyan.jobs.review_segment_tokenization import run_review_segment_tokenization
    from wenyan.jobs.split_paragraphs import run_split_paragraphs
    from wenyan.jobs.split_segments import run_split_segments
    from wenyan.jobs.tokenize_segment import run_tokenize_segment
    from wenyan_models.domain.targets import single_segment_target

    source_dir = tmp_workspace / "sources" / "documents" / "sunzi-bingfa"
    doc_id = run_ingest_document(ctx, source_dir, JobOptions()).artifact  # type: ignore[union-attr]
    chapter_proposal = install_sunzi_chapter_proposal(ctx, doc_id)
    chapter_id_value = chapter_proposal.chapters[0].id
    paragraphs = run_split_paragraphs(ctx, doc_id, chapter_id_value, JobOptions()).artifact  # type: ignore[union-attr]
    first_paragraph_id = paragraphs.paragraphs[0].id
    draft = run_split_segments(ctx, doc_id, first_paragraph_id, JobOptions()).artifact  # type: ignore[union-attr]
    first_segment_id = draft.segments[0].id
    run_tokenize_segment(ctx, doc_id, single_segment_target(first_segment_id), JobOptions())
    run_review_segment_tokenization(ctx, doc_id, first_segment_id, JobOptions())

    work = find_next_segment_work(ctx.artifacts, doc_id)
    assert work is not None
    assert work.segment_id == first_segment_id


def test_run_next_paragraph_split_segments(tmp_workspace: Path) -> None:
    ctx = build_job_context(tmp_workspace)
    from wenyan.jobs.ingest_document import run_ingest_document
    from wenyan.jobs.split_paragraphs import run_split_paragraphs

    source_dir = tmp_workspace / "sources" / "documents" / "sunzi-bingfa"
    doc_id = run_ingest_document(ctx, source_dir, JobOptions()).artifact  # type: ignore[union-attr]
    chapter_proposal = install_sunzi_chapter_proposal(ctx, doc_id)
    chapter_id_value = chapter_proposal.chapters[0].id
    run_split_paragraphs(ctx, doc_id, chapter_id_value, JobOptions())

    outcome = run_preprocess(
        ctx,
        doc_id,
        next_paragraph=True,
        options=JobOptions(),
    )
    assert outcome.kind == "promoted"
    assert outcome.artifact.stages_run == ("split-segments",)  # type: ignore[union-attr]


def test_run_segment_stops_at_skill_driven_context_subjobs(tmp_workspace: Path) -> None:
    ctx = build_job_context(tmp_workspace)
    from wenyan.jobs.ingest_document import run_ingest_document
    from wenyan.jobs.split_paragraphs import run_split_paragraphs
    from wenyan.jobs.split_segments import run_split_segments

    source_dir = tmp_workspace / "sources" / "documents" / "sunzi-bingfa"
    doc_id = run_ingest_document(ctx, source_dir, JobOptions()).artifact  # type: ignore[union-attr]
    chapter_proposal = install_sunzi_chapter_proposal(ctx, doc_id)
    chapter_id_value = chapter_proposal.chapters[0].id
    paragraphs = run_split_paragraphs(ctx, doc_id, chapter_id_value, JobOptions()).artifact  # type: ignore[union-attr]
    first_paragraph_id = paragraphs.paragraphs[0].id
    draft = run_split_segments(ctx, doc_id, first_paragraph_id, JobOptions()).artifact  # type: ignore[union-attr]
    first_segment_id = draft.segments[0].id

    outcome = run_preprocess(
        ctx,
        doc_id,
        segment_id_value=first_segment_id,
        options=JobOptions(),
    )
    assert outcome.kind == "failure"
    assert outcome.code == "not-implemented"  # type: ignore[union-attr]
    assert "drafting-context-notes" in outcome.message  # type: ignore[union-attr]
    assert "review-segment-grammar" in outcome.message  # type: ignore[union-attr]
    assert "annotate-segment-context" in outcome.message  # type: ignore[union-attr]
    assert "review-segment-context" not in outcome.message  # type: ignore[union-attr]
