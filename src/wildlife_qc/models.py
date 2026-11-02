"""Small, serializable data models used by the validation engine."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Literal

Severity = Literal["error", "warning", "info"]


@dataclass(frozen=True, slots=True)
class Issue:
    """One actionable data-quality finding."""

    severity: Severity
    code: str
    message: str
    suggestion: str
    row: int | None = None
    field: str | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(slots=True)
class ValidationReport:
    """Summary of a single input file validation run."""

    source: str
    profile: str
    rows_checked: int = 0
    columns: list[str] = field(default_factory=list)
    issues: list[Issue] = field(default_factory=list)

    @property
    def errors(self) -> int:
        return sum(issue.severity == "error" for issue in self.issues)

    @property
    def warnings(self) -> int:
        return sum(issue.severity == "warning" for issue in self.issues)

    @property
    def info(self) -> int:
        return sum(issue.severity == "info" for issue in self.issues)

    @property
    def passed(self) -> bool:
        return self.errors == 0

    def to_dict(self) -> dict[str, object]:
        return {
            "source": self.source,
            "profile": self.profile,
            "rows_checked": self.rows_checked,
            "columns": self.columns,
            "summary": {
                "passed": self.passed,
                "errors": self.errors,
                "warnings": self.warnings,
                "info": self.info,
            },
            "issues": [issue.to_dict() for issue in self.issues],
        }
