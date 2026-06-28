from wenyan_models.domain.results import JobFailure, Promoted, Skipped, outcome_exit_code


def test_outcome_exit_code_success() -> None:
    assert outcome_exit_code(Skipped(reason="already exists")) == 0
    promoted = Promoted(artifact={"id": "x"})
    assert outcome_exit_code(promoted) == 0
    assert promoted.kind == "promoted"


def test_outcome_exit_code_failure() -> None:
    assert (
        outcome_exit_code(JobFailure(code="validation", message="span overlap"))
        == 1
    )
