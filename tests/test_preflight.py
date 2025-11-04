import pytest

from src.preflight import PreflightChecker, PreflightIssue


class StubComponent:
    def __init__(self, issues=None):
        self._issues = issues or []

    def preflight_check(self):
        return self._issues


def test_preflight_no_issues():
    checker = PreflightChecker(
        transcriber=StubComponent(),
        diarizer=StubComponent(),
        classifier=StubComponent(),
    )
    checker.verify(skip_diarization=False, skip_classification=False)


def test_preflight_warning_does_not_raise(caplog):
    warning_issue = PreflightIssue(component="transcriber", message="GPU not found", severity="warning")
    checker = PreflightChecker(
        transcriber=StubComponent([warning_issue]),
        diarizer=StubComponent(),
        classifier=StubComponent(),
    )

    checker.verify(skip_diarization=False, skip_classification=False)

    records = [record for record in caplog.records if record.levelname == "WARNING"]
    assert records, "Expected warning to be logged"


def test_preflight_error_raises():
    error_issue = PreflightIssue(component="classifier", message="Ollama offline", severity="error")
    checker = PreflightChecker(
        transcriber=StubComponent(),
        diarizer=StubComponent(),
        classifier=StubComponent([error_issue]),
    )

    with pytest.raises(RuntimeError) as exc:
        checker.verify(skip_diarization=False, skip_classification=False)

    assert "Preflight checks failed" in str(exc.value)


def test_preflight_respects_skip_flags():
    error_issue = PreflightIssue(component="classifier", message="Ollama offline", severity="error")
    checker = PreflightChecker(
        transcriber=StubComponent(),
        diarizer=StubComponent(),
        classifier=StubComponent([error_issue]),
    )

    # Skip classification so the error should not trigger
    checker.verify(skip_diarization=False, skip_classification=True)

