from pathlib import Path

from wenyan.bootstrap import build_job_context
from wenyan.core.ports.artifact_ref import (
    segment_grammar_notes_ref,
    segment_grammar_review_ref,
)
from wenyan.jobs.annotate_segment_context import run_annotate_segment_context
from wenyan.jobs.annotate_segment_grammar import run_annotate_segment_grammar
from wenyan.jobs.context import JobOptions
from wenyan.jobs.ingest_document import run_ingest_document
from wenyan.jobs.review_segment_context import run_review_segment_context
from wenyan.jobs.review_segment_grammar import run_review_segment_grammar
from wenyan.jobs.review_segment_tokenization import run_review_segment_tokenization
from wenyan.jobs.split_paragraphs import run_split_paragraphs
from wenyan.jobs.split_segments import run_split_segments
from wenyan.jobs.tokenize_segment import run_tokenize_segment
from wenyan_models.artifacts.segment import GrammarNotesArtifact, GrammarReviewArtifact
from wenyan_models.domain.enums import ReviewStatus
from wenyan_models.domain.results import JobFailure, Promoted, Skipped, outcome_exit_code
from wenyan_models.domain.targets import single_segment_target
from conftest import install_sunzi_chapter_proposal


def _prepare_segment_with_approved_tokenization(tmp_workspace: Path) -> tuple[object, object]:
    ctx = build_job_context(tmp_workspace)
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
    return ctx, (doc_id, first_segment_id)


def test_annotate_segment_grammar_requires_approved_tokenization_review(tmp_workspace: Path) -> None:
    ctx = build_job_context(tmp_workspace)
    source_dir = tmp_workspace / "sources" / "documents" / "sunzi-bingfa"
    doc_id = run_ingest_document(ctx, source_dir, JobOptions()).artifact  # type: ignore[union-attr]
    chapter_proposal = install_sunzi_chapter_proposal(ctx, doc_id)
    chapter_id_value = chapter_proposal.chapters[0].id
    paragraphs = run_split_paragraphs(ctx, doc_id, chapter_id_value, JobOptions()).artifact  # type: ignore[union-attr]
    first_paragraph_id = paragraphs.paragraphs[0].id
    draft = run_split_segments(ctx, doc_id, first_paragraph_id, JobOptions()).artifact  # type: ignore[union-attr]
    first_segment_id = draft.segments[0].id
    run_tokenize_segment(ctx, doc_id, single_segment_target(first_segment_id), JobOptions())

    outcome = run_annotate_segment_grammar(
        ctx,
        doc_id,
        single_segment_target(first_segment_id),
        JobOptions(),
    )
    assert isinstance(outcome, JobFailure)
    assert outcome.code == "missing-input"


def test_annotate_segment_grammar_writes_artifact(tmp_workspace: Path) -> None:
    ctx, (doc_id, segment_id_value) = _prepare_segment_with_approved_tokenization(tmp_workspace)

    outcome = run_annotate_segment_grammar(
        ctx,
        doc_id,
        single_segment_target(segment_id_value),
        JobOptions(),
    )
    assert outcome_exit_code(outcome) == 0
    assert isinstance(outcome, Promoted)
    grammar_ref = segment_grammar_notes_ref(doc_id, segment_id_value)
    assert ctx.artifacts.exists(grammar_ref)
    grammar = ctx.artifacts.read(grammar_ref, GrammarNotesArtifact)
    assert all(note.anchor_token_ids for note in grammar.grammar_notes)


def test_annotate_segment_grammar_skips_current_artifact(tmp_workspace: Path) -> None:
    ctx, (doc_id, segment_id_value) = _prepare_segment_with_approved_tokenization(tmp_workspace)
    run_annotate_segment_grammar(ctx, doc_id, single_segment_target(segment_id_value), JobOptions())

    outcome = run_annotate_segment_grammar(
        ctx,
        doc_id,
        single_segment_target(segment_id_value),
        JobOptions(),
    )
    assert isinstance(outcome, Skipped)


def test_review_segment_grammar_approves(tmp_workspace: Path) -> None:
    ctx, (doc_id, segment_id_value) = _prepare_segment_with_approved_tokenization(tmp_workspace)
    run_annotate_segment_grammar(ctx, doc_id, single_segment_target(segment_id_value), JobOptions())

    outcome = run_review_segment_grammar(ctx, doc_id, segment_id_value, JobOptions())
    assert outcome_exit_code(outcome) == 0
    assert isinstance(outcome, Promoted)
    review = ctx.artifacts.read(
        segment_grammar_review_ref(doc_id, segment_id_value),
        GrammarReviewArtifact,
    )
    assert review.status == ReviewStatus.APPROVED


def test_review_segment_grammar_rejects(tmp_workspace: Path, monkeypatch) -> None:
    from wenyan.core.adapters import mock_llm_client

    original = mock_llm_client.MockLLMClient._grammar_review

    def reject_review(self, prompt, model):  # type: ignore[no-untyped-def]
        result = original(self, prompt, model)
        return result.model_copy(update={"status": ReviewStatus.REJECTED})

    monkeypatch.setattr(mock_llm_client.MockLLMClient, "_grammar_review", reject_review)

    ctx, (doc_id, segment_id_value) = _prepare_segment_with_approved_tokenization(tmp_workspace)
    run_annotate_segment_grammar(ctx, doc_id, single_segment_target(segment_id_value), JobOptions())

    outcome = run_review_segment_grammar(ctx, doc_id, segment_id_value, JobOptions())
    assert isinstance(outcome, JobFailure)
    assert outcome.code == "review-rejected"


def test_annotate_segment_context_is_skill_driven_stub(tmp_workspace: Path) -> None:
    ctx, (doc_id, segment_id_value) = _prepare_segment_with_approved_tokenization(tmp_workspace)

    outcome = run_annotate_segment_context(
        ctx,
        doc_id,
        single_segment_target(segment_id_value),
        JobOptions(),
    )
    assert isinstance(outcome, JobFailure)
    assert outcome.code == "not-implemented"
    assert "drafting-context-notes" in outcome.message


def test_review_segment_context_is_skill_driven_stub(tmp_workspace: Path) -> None:
    ctx, (doc_id, segment_id_value) = _prepare_segment_with_approved_tokenization(tmp_workspace)

    outcome = run_review_segment_context(ctx, doc_id, segment_id_value, JobOptions())
    assert isinstance(outcome, JobFailure)
    assert outcome.code == "not-implemented"
    assert "reviewing-context-notes" in outcome.message
