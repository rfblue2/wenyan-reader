from pathlib import Path

from wenyan.bootstrap import build_job_context
from wenyan.core.ports.artifact_ref import (
    segment_gloss_review_ref,
    segment_glosses_ref,
    segment_grammar_notes_ref,
    segment_grammar_review_ref,
    segment_tokenization_review_ref,
)
from wenyan.jobs.annotate_segment_grammar import run_annotate_segment_grammar
from wenyan.jobs.context import JobOptions
from wenyan.jobs.gloss_segment import run_gloss_segment
from wenyan.jobs.ingest_document import run_ingest_document
from wenyan.jobs.review_segment_gloss import run_review_segment_gloss
from wenyan.jobs.review_segment_grammar import run_review_segment_grammar
from wenyan.jobs.review_segment_tokenization import run_review_segment_tokenization
from wenyan.jobs.split_paragraphs import run_split_paragraphs
from wenyan.jobs.split_segments import run_split_segments
from wenyan.jobs.tokenize_segment import run_tokenize_segment
from wenyan_models.domain.results import Promoted
from wenyan_models.domain.targets import single_segment_target
from conftest import install_sunzi_chapter_proposal


def _prepare_segment(tmp_workspace: Path) -> tuple[object, object, object]:
    ctx = build_job_context(tmp_workspace)
    source_dir = tmp_workspace / "sources" / "documents" / "sunzi-bingfa"
    doc_id = run_ingest_document(ctx, source_dir, JobOptions()).artifact  # type: ignore[union-attr]
    chapter_proposal = install_sunzi_chapter_proposal(ctx, doc_id)
    chapter_id_value = chapter_proposal.chapters[0].id
    paragraphs = run_split_paragraphs(ctx, doc_id, chapter_id_value, JobOptions()).artifact  # type: ignore[union-attr]
    first_paragraph_id = paragraphs.paragraphs[0].id
    draft = run_split_segments(ctx, doc_id, first_paragraph_id, JobOptions()).artifact  # type: ignore[union-attr]
    first_segment_id = draft.segments[0].id
    return ctx, doc_id, first_segment_id


def test_tokenize_segment_deletes_tokenization_review_on_rerun(tmp_workspace: Path) -> None:
    ctx, doc_id, segment_id_value = _prepare_segment(tmp_workspace)
    target = single_segment_target(segment_id_value)
    run_tokenize_segment(ctx, doc_id, target, JobOptions())
    run_review_segment_tokenization(ctx, doc_id, segment_id_value, JobOptions())
    review_ref = segment_tokenization_review_ref(doc_id, segment_id_value)
    assert ctx.artifacts.exists(review_ref)

    outcome = run_tokenize_segment(ctx, doc_id, target, JobOptions(force=True))
    assert isinstance(outcome, Promoted)
    assert not ctx.artifacts.exists(review_ref)


def test_gloss_segment_deletes_gloss_review_on_rerun(tmp_workspace: Path) -> None:
    ctx, doc_id, segment_id_value = _prepare_segment(tmp_workspace)
    target = single_segment_target(segment_id_value)
    run_tokenize_segment(ctx, doc_id, target, JobOptions())
    run_review_segment_tokenization(ctx, doc_id, segment_id_value, JobOptions())
    run_gloss_segment(ctx, doc_id, target, JobOptions())
    run_review_segment_gloss(ctx, doc_id, segment_id_value, JobOptions())
    review_ref = segment_gloss_review_ref(doc_id, segment_id_value)
    assert ctx.artifacts.exists(review_ref)

    outcome = run_gloss_segment(ctx, doc_id, target, JobOptions(force=True))
    assert isinstance(outcome, Promoted)
    assert not ctx.artifacts.exists(review_ref)


def test_annotate_segment_grammar_deletes_grammar_review_on_rerun(tmp_workspace: Path) -> None:
    ctx, doc_id, segment_id_value = _prepare_segment(tmp_workspace)
    target = single_segment_target(segment_id_value)
    run_tokenize_segment(ctx, doc_id, target, JobOptions())
    run_review_segment_tokenization(ctx, doc_id, segment_id_value, JobOptions())
    run_annotate_segment_grammar(ctx, doc_id, target, JobOptions())
    run_review_segment_grammar(ctx, doc_id, segment_id_value, JobOptions())
    review_ref = segment_grammar_review_ref(doc_id, segment_id_value)
    assert ctx.artifacts.exists(review_ref)

    outcome = run_annotate_segment_grammar(ctx, doc_id, target, JobOptions(force=True))
    assert isinstance(outcome, Promoted)
    assert not ctx.artifacts.exists(review_ref)
    assert ctx.artifacts.exists(segment_grammar_notes_ref(doc_id, segment_id_value))
