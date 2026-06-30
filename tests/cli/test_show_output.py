from pathlib import Path

from wenyan.bootstrap import build_job_context
from wenyan.cli.status_output import StatusDisplayContext, render_status
from wenyan.cli.status_scope import resolve_status_scope, segment_handle_for_id
from wenyan.core.ports.artifact_ref import segment_context_notes_ref, segment_grammar_notes_ref
from wenyan.core.show.segment_view import build_segment_show_view
from wenyan.jobs.context import JobOptions
from wenyan.jobs.gloss_segment import run_gloss_segment
from wenyan.jobs.ingest_document import run_ingest_document
from wenyan.jobs.review_segment_gloss import run_review_segment_gloss
from wenyan.jobs.review_segment_tokenization import run_review_segment_tokenization
from wenyan.jobs.split_paragraphs import run_split_paragraphs
from wenyan.jobs.split_segments import run_split_segments
from wenyan.jobs.tokenize_segment import run_tokenize_segment
from wenyan_models.domain.enums import ReviewStatus, UnitStatus
from wenyan_models.domain.targets import single_segment_target
from wenyan_models.artifacts.segment import (
    ContextNotesArtifact,
    GrammarNoteItem,
    GrammarNotesArtifact,
    NoteCitation,
    ContextNoteItem,
)
from conftest import install_sunzi_chapter_proposal


def _prepare_segment_tokenized(tmp_workspace: Path) -> tuple[object, object, object]:
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
    return ctx, doc_id, first_segment_id


def _prepare_segment_with_glosses(tmp_workspace: Path) -> tuple[object, object, object]:
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
    run_gloss_segment(ctx, doc_id, single_segment_target(first_segment_id), JobOptions())
    run_review_segment_gloss(ctx, doc_id, first_segment_id, JobOptions())
    return ctx, doc_id, first_segment_id


def test_build_segment_show_view_includes_gloss_rows(tmp_workspace: Path) -> None:
    ctx, doc_id, segment_id_value = _prepare_segment_with_glosses(tmp_workspace)

    payload = build_segment_show_view(
        ctx.artifacts,
        tmp_workspace,
        document_id=doc_id,
        document_ref="sunzi-bingfa",
        segment_id=segment_id_value,
        chapter_handle="1",
        paragraph_handle="1",
        segment_handle="1",
    )

    assert payload.text
    assert len(payload.tokens) >= 1
    assert all(row.surface for row in payload.tokens)
    assert any(row.gloss is not None for row in payload.tokens)
    assert payload.status in {UnitStatus.COMPLETE, UnitStatus.BLOCKED, UnitStatus.IN_PROGRESS}
    gloss_review = next(
        (review for review in payload.reviews if review.kind.value == "review-segment-gloss"),
        None,
    )
    assert gloss_review is not None
    assert gloss_review.status == ReviewStatus.APPROVED


def test_render_segment_show_displays_gloss_table(tmp_workspace: Path) -> None:
    ctx, doc_id, segment_id_value = _prepare_segment_with_glosses(tmp_workspace)
    payload = build_segment_show_view(
        ctx.artifacts,
        tmp_workspace,
        document_id=doc_id,
        document_ref="sunzi-bingfa",
        segment_id=segment_id_value,
        chapter_handle="1",
        paragraph_handle="1",
        segment_handle="1",
    )

    output = render_status(
        payload,
        StatusDisplayContext(chapter_handle="1", paragraph_handle="1", segment_handle="1"),
    )

    assert "sunzi-bingfa" in output
    assert "Chapter #1" in output
    assert "Paragraph #1" in output
    assert "Segment #1" in output
    assert payload.text in output
    assert "Glosses" in output
    assert "review-segment-gloss" in output
    assert "Components" in output


def test_resolve_segment_by_ordinal_for_show(tmp_workspace: Path) -> None:
    ctx, doc_id, segment_id_value = _prepare_segment_with_glosses(tmp_workspace)
    scope = resolve_status_scope(
        ctx.artifacts,
        doc_id,
        "sunzi-bingfa",
        chapter="1",
        paragraph="1",
        segment="1",
    )
    assert scope.segment_id == segment_id_value
    assert scope.segment_handle == "1"
    handle = segment_handle_for_id(
        ctx.artifacts,
        doc_id,
        scope.paragraph_id,  # type: ignore[arg-type]
        segment_id_value,
    )
    assert handle == "1"


def test_render_segment_show_tokenization_only(tmp_workspace: Path) -> None:
    ctx, doc_id, segment_id_value = _prepare_segment_tokenized(tmp_workspace)
    payload = build_segment_show_view(
        ctx.artifacts,
        tmp_workspace,
        document_id=doc_id,
        document_ref="sunzi-bingfa",
        segment_id=segment_id_value,
    )
    output = render_status(payload, StatusDisplayContext())

    assert len(payload.tokens) >= 1
    assert all(row.gloss is None for row in payload.tokens)
    assert "Glosses" not in output
    assert payload.tokens[0].surface in output


def test_render_segment_show_rejected_gloss_review(tmp_workspace: Path, monkeypatch) -> None:
    from wenyan.core.adapters import mock_llm_client

    original = mock_llm_client.MockLLMClient._gloss_review

    def reject_review(self, prompt, model):  # type: ignore[no-untyped-def]
        result = original(self, prompt, model)
        return result.model_copy(
            update={
                "status": ReviewStatus.REJECTED,
                "findings": ({"severity": "error", "message": "Wrong sense for 之."},),
            },
        )

    monkeypatch.setattr(mock_llm_client.MockLLMClient, "_gloss_review", reject_review)

    ctx, doc_id, segment_id_value = _prepare_segment_tokenized(tmp_workspace)
    run_review_segment_tokenization(ctx, doc_id, segment_id_value, JobOptions())
    run_gloss_segment(ctx, doc_id, single_segment_target(segment_id_value), JobOptions())
    run_review_segment_gloss(ctx, doc_id, segment_id_value, JobOptions())
    payload = build_segment_show_view(
        ctx.artifacts,
        tmp_workspace,
        document_id=doc_id,
        document_ref="sunzi-bingfa",
        segment_id=segment_id_value,
    )
    output = render_status(payload, StatusDisplayContext())

    assert "rejected" in output
    assert "Wrong sense for 之." in output
    gloss_review = next(
        review for review in payload.reviews if review.kind.value == "review-segment-gloss"
    )
    assert gloss_review.status == ReviewStatus.REJECTED


def test_render_segment_show_displays_context_review_findings(tmp_workspace: Path) -> None:
    from wenyan.core.ports.artifact_ref import segment_context_review_ref
    from wenyan_models.artifacts.segment import ContextReviewArtifact

    ctx, doc_id, segment_id_value = _prepare_segment_with_glosses(tmp_workspace)
    ctx.artifacts.write(
        segment_context_review_ref(doc_id, segment_id_value),
        ContextReviewArtifact(
            segmentId=segment_id_value,
            model="mock",
            inputHash="sha256:test",
            attempts=1,
            status=ReviewStatus.REJECTED,
            findings=(
                {
                    "noteId": "note-1",
                    "reason": "Unsupported historical claim without sources.",
                },
            ),
        ),
        dry_run=False,
    )
    payload = build_segment_show_view(
        ctx.artifacts,
        tmp_workspace,
        document_id=doc_id,
        document_ref="sunzi-bingfa",
        segment_id=segment_id_value,
    )
    output = render_status(payload, StatusDisplayContext())

    assert "Unsupported historical claim without sources." in output
    context_review = next(
        review for review in payload.reviews if review.kind.value == "review-segment-context"
    )
    assert len(context_review.finding_lines) == 1


def test_build_segment_show_view_includes_notes(tmp_workspace: Path) -> None:
    ctx, doc_id, segment_id_value = _prepare_segment_with_glosses(tmp_workspace)
    token_id = build_segment_show_view(
        ctx.artifacts,
        tmp_workspace,
        document_id=doc_id,
        document_ref="sunzi-bingfa",
        segment_id=segment_id_value,
    ).tokens[0].token_id
    grammar = GrammarNotesArtifact(
        segmentId=segment_id_value,
        model="mock",
        inputHash="sha256:test",
        attempts=1,
        grammarNotes=(
            GrammarNoteItem(
                id="note-1",
                anchorTokenIds=(token_id,),
                body="Title segment heading.",
            ),
        ),
    )
    ctx.artifacts.write(segment_grammar_notes_ref(doc_id, segment_id_value), grammar, dry_run=False)
    ctx.artifacts.write(
        segment_context_notes_ref(doc_id, segment_id_value),
        ContextNotesArtifact(
            segmentId=segment_id_value,
            model="mock",
            inputHash="sha256:test",
            attempts=1,
            contextNotes=(
                ContextNoteItem(
                    id="note-2",
                    anchorTokenIds=(token_id,),
                    body="Chapter title for 始計.",
                    sources=(
                        NoteCitation(
                            label="Commentary",
                            excerpt="Chapter heading context.",
                        ),
                    ),
                ),
            ),
        ),
        dry_run=False,
    )

    payload = build_segment_show_view(
        ctx.artifacts,
        tmp_workspace,
        document_id=doc_id,
        document_ref="sunzi-bingfa",
        segment_id=segment_id_value,
    )

    assert len(payload.grammar_notes) == 1
    assert payload.grammar_notes[0].body == "Title segment heading."
    assert payload.grammar_notes[0].anchor_surfaces == (payload.tokens[0].surface,)
    assert len(payload.context_notes) == 1
    assert payload.context_notes[0].sources[0].label == "Commentary"


def test_render_segment_show_displays_notes(tmp_workspace: Path) -> None:
    ctx, doc_id, segment_id_value = _prepare_segment_with_glosses(tmp_workspace)
    token_id = build_segment_show_view(
        ctx.artifacts,
        tmp_workspace,
        document_id=doc_id,
        document_ref="sunzi-bingfa",
        segment_id=segment_id_value,
    ).tokens[0].token_id
    ctx.artifacts.write(
        segment_grammar_notes_ref(doc_id, segment_id_value),
        GrammarNotesArtifact(
            segmentId=segment_id_value,
            model="mock",
            inputHash="sha256:test",
            attempts=1,
            grammarNotes=(
                GrammarNoteItem(
                    id="note-1",
                    anchorTokenIds=(token_id,),
                    body="Title segment heading.",
                ),
            ),
        ),
        dry_run=False,
    )
    payload = build_segment_show_view(
        ctx.artifacts,
        tmp_workspace,
        document_id=doc_id,
        document_ref="sunzi-bingfa",
        segment_id=segment_id_value,
    )
    output = render_status(payload, StatusDisplayContext())

    assert "Grammar notes" in output
    assert "Title segment heading." in output
    assert payload.tokens[0].surface in output
