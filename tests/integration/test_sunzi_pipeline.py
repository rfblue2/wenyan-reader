from pathlib import Path


from wenyan.bootstrap import build_job_context
from wenyan.jobs.context import JobOptions
from wenyan.jobs.ingest_document import run_ingest_document
from wenyan.jobs.gloss_segment import run_gloss_segment
from wenyan.jobs.review_segment_gloss import run_review_segment_gloss
from wenyan.jobs.review_segment_tokenization import run_review_segment_tokenization
from wenyan.jobs.split_paragraphs import run_split_paragraphs
from wenyan.jobs.split_segments import run_split_segments
from wenyan.jobs.tokenize_segment import run_tokenize_segment
from wenyan_models.domain.results import Promoted, outcome_exit_code
from wenyan_models.domain.targets import single_segment_target
from conftest import install_sunzi_chapter_proposal


def test_sunzi_pipeline(tmp_workspace: Path) -> None:
    ctx = build_job_context(tmp_workspace)
    source_dir = tmp_workspace / "sources" / "documents" / "sunzi-bingfa"
    ingest_outcome = run_ingest_document(ctx, source_dir, JobOptions())
    assert outcome_exit_code(ingest_outcome) == 0
    assert isinstance(ingest_outcome, Promoted)
    doc_id = ingest_outcome.artifact

    chapter_proposal = install_sunzi_chapter_proposal(ctx, doc_id)
    chapter_id_value = chapter_proposal.chapters[0].id

    paragraphs_outcome = run_split_paragraphs(
        ctx,
        doc_id,
        chapter_id_value,
        JobOptions(),
    )
    assert outcome_exit_code(paragraphs_outcome) == 0
    assert isinstance(paragraphs_outcome, Promoted)
    paragraph_id_value = paragraphs_outcome.artifact.paragraphs[0].id

    segments_outcome = run_split_segments(ctx, doc_id, paragraph_id_value, JobOptions())
    assert outcome_exit_code(segments_outcome) == 0
    assert isinstance(segments_outcome, Promoted)
    segment_id_value = segments_outcome.artifact.segments[0].id

    tokenize_outcome = run_tokenize_segment(
        ctx,
        doc_id,
        single_segment_target(segment_id_value),
        JobOptions(),
    )
    assert outcome_exit_code(tokenize_outcome) == 0

    review_outcome = run_review_segment_tokenization(
        ctx,
        doc_id,
        segment_id_value,
        JobOptions(),
    )
    assert outcome_exit_code(review_outcome) == 0

    gloss_outcome = run_gloss_segment(
        ctx,
        doc_id,
        single_segment_target(segment_id_value),
        JobOptions(),
    )
    assert outcome_exit_code(gloss_outcome) == 0

    gloss_review_outcome = run_review_segment_gloss(
        ctx,
        doc_id,
        segment_id_value,
        JobOptions(),
    )
    assert outcome_exit_code(gloss_review_outcome) == 0
