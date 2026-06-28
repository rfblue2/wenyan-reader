from pathlib import Path


from wenyan.bootstrap import build_job_context
from wenyan.jobs.context import JobOptions
from wenyan.jobs.ingest_document import run_ingest_document
from wenyan_models.domain.results import Promoted, outcome_exit_code


def test_ingest_document(tmp_workspace: Path) -> None:
    ctx = build_job_context(tmp_workspace)
    source_dir = tmp_workspace / "sources" / "documents" / "sunzi-bingfa"
    outcome = run_ingest_document(ctx, source_dir, JobOptions())
    assert outcome_exit_code(outcome) == 0
    assert isinstance(outcome, Promoted)
