"""Environment readiness checks before starting processing."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Protocol
from .logger import get_logger


class SupportsPreflight(Protocol):
    """Protocol for components that can report preflight readiness issues."""

    def preflight_check(self) -> Iterable["PreflightIssue"]:
        ...


@dataclass
class PreflightIssue:
    """Represents an issue detected during preflight checks."""

    component: str
    message: str
    severity: str = "error"  # "error" or "warning"

    def is_error(self) -> bool:
        return self.severity.lower() == "error"


class PreflightChecker:
    """Aggregates preflight checks for pipeline components."""

    def __init__(
        self,
        transcriber: SupportsPreflight,
        diarizer: SupportsPreflight,
        classifier: SupportsPreflight,
    ):
        self.transcriber = transcriber
        self.diarizer = diarizer
        self.classifier = classifier
        self.logger = get_logger("preflight")

    def verify(
        self,
        *,
        skip_diarization: bool,
        skip_classification: bool,
    ) -> None:
        """Run preflight checks and raise if any blocking issues are found."""
        issues = self.collect_issues(
            skip_diarization=skip_diarization,
            skip_classification=skip_classification,
        )
        if not issues:
            return

        for issue in issues:
            log_method = (
                self.logger.error if issue.is_error() else self.logger.warning
            )
            log_method("[%s] %s", issue.component, issue.message)

        errors = [issue for issue in issues if issue.is_error()]
        if errors:
            bullet_list = "\n".join(
                f"- {issue.component}: {issue.message}" for issue in errors
            )
            raise RuntimeError(f"Preflight checks failed:\n{bullet_list}")

    def collect_issues(
        self,
        *,
        skip_diarization: bool,
        skip_classification: bool,
    ) -> List[PreflightIssue]:
        """Collect all preflight issues without logging or raising."""
        issues: List[PreflightIssue] = []

        issues.extend(self._collect("transcriber", self.transcriber.preflight_check()))

        if not skip_diarization:
            issues.extend(self._collect("diarizer", self.diarizer.preflight_check()))

        if not skip_classification:
            issues.extend(
                self._collect("classifier", self.classifier.preflight_check())
            )

        return issues

    @staticmethod
    def _collect(
        component_name: str, items: Iterable[PreflightIssue]
    ) -> List[PreflightIssue]:
        """Ensure collected issues have the component field set."""
        results: List[PreflightIssue] = []
        for issue in items:
            if not issue.component:
                issue.component = component_name
            results.append(issue)
        return results
