from pathlib import Path

from wenyan.bootstrap import build_job_context
from wenyan.core.adapters.hashing import sha256_text
from wenyan.core.ports.artifact_ref import (
    segment_context_notes_ref,
    segment_context_review_ref,
)
from wenyan.jobs.annotate_segment_grammar import run_annotate_segment_grammar
from wenyan.jobs.context import JobContext, JobOptions
from wenyan.jobs.gloss_segment import run_gloss_segment
from wenyan.jobs.ingest_document import run_ingest_document
from wenyan.jobs.review_segment_gloss import run_review_segment_gloss
from wenyan.jobs.review_segment_grammar import run_review_segment_grammar
from wenyan.jobs.review_segment_tokenization import run_review_segment_tokenization
from wenyan.jobs.split_paragraphs import run_split_paragraphs
from wenyan.jobs.split_segments import run_split_segments
from wenyan.jobs.tokenize_segment import run_tokenize_segment
from wenyan_models.artifacts.segment import ContextNotesArtifact, ContextReviewArtifact
from wenyan_models.domain.enums import ReviewStatus
from wenyan_models.domain.ids import DocumentId, ParagraphId, SegmentId
from wenyan_models.domain.results import outcome_exit_code
from wenyan_models.domain.targets import single_segment_target
from conftest import install_sunzi_chapter_proposal


def prepare_paragraph_with_complete_segments(
    tmp_workspace: Path,
) -> tuple[JobContext, DocumentId, ParagraphId]:
    ctx = build_job_context(tmp_workspace)
    source_dir = tmp_workspace / "sources" / "documents" / "sunzi-bingfa"
    doc_id = run_ingest_document(ctx, source_dir, JobOptions()).artifact  # type: ignore[union-attr]
    chapter_proposal = install_sunzi_chapter_proposal(ctx, doc_id)
    chapter_id_value = chapter_proposal.chapters[0].id
    paragraphs = run_split_paragraphs(ctx, doc_id, chapter_id_value, JobOptions()).artifact  # type: ignore[union-attr]
    paragraph_id_value = paragraphs.paragraphs[0].id
    draft = run_split_segments(ctx, doc_id, paragraph_id_value, JobOptions()).artifact  # type: ignore[union-attr]
    for segment in draft.segments:
        _complete_segment_subjobs(ctx, doc_id, segment.id)
    return ctx, doc_id, paragraph_id_value


def _complete_segment_subjobs(
    ctx: JobContext,
    document_id: DocumentId,
    segment_id_value: SegmentId,
) -> None:
    options = JobOptions()
    runners = (
        lambda: run_tokenize_segment(ctx, document_id, single_segment_target(segment_id_value), options),
        lambda: run_review_segment_tokenization(ctx, document_id, segment_id_value, options),
        lambda: run_gloss_segment(ctx, document_id, single_segment_target(segment_id_value), options),
        lambda: run_review_segment_gloss(ctx, document_id, segment_id_value, options),
        lambda: run_annotate_segment_grammar(ctx, document_id, single_segment_target(segment_id_value), options),
        lambda: run_review_segment_grammar(ctx, document_id, segment_id_value, options),
    )
    for runner in runners:
        outcome = runner()
        if outcome_exit_code(outcome) != 0:
            raise AssertionError(f"segment subjob failed for {segment_id_value}: {outcome}")
    _write_approved_context_artifacts(ctx, document_id, segment_id_value)


def _write_approved_context_artifacts(
    ctx: JobContext,
    document_id: DocumentId,
    segment_id_value: SegmentId,
) -> None:
    context_notes = ContextNotesArtifact(
        segment_id=segment_id_value,
        input_hash=sha256_text(f"context-notes:{segment_id_value}"),
        model="test",
        attempts=1,
        context_notes=(),
    )
    ctx.artifacts.write(
        segment_context_notes_ref(document_id, segment_id_value),
        context_notes,
        dry_run=False,
    )
    context_review = ContextReviewArtifact(
        segment_id=segment_id_value,
        input_hash=sha256_text(context_notes.model_dump_json(by_alias=True)),
        model="test",
        attempts=1,
        status=ReviewStatus.APPROVED,
    )
    ctx.artifacts.write(
        segment_context_review_ref(document_id, segment_id_value),
        context_review,
        dry_run=False,
    )
