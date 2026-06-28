from pathlib import Path


from wenyan.bootstrap import build_job_context
from wenyan.jobs.context import JobOptions
from wenyan.jobs.ingest_document import run_ingest_document
from wenyan.jobs.split_chapters import run_split_chapters
from wenyan_models.domain.results import Promoted, outcome_exit_code


def test_split_chapters(tmp_workspace: Path) -> None:
    ctx = build_job_context(tmp_workspace)
    source_dir = tmp_workspace / "sources" / "documents" / "sunzi-bingfa"
    ingest = run_ingest_document(ctx, source_dir, JobOptions())
    assert isinstance(ingest, Promoted)
    outcome = run_split_chapters(ctx, ingest.artifact, JobOptions())
    assert outcome_exit_code(outcome) == 0
    assert isinstance(outcome, Promoted)
    assert len(outcome.artifact.chapters) == 13
