from dataclasses import dataclass
from datetime import timedelta
from typing import Literal

OperationalSeverity = Literal[
    "info",
    "warning",
    "critical",
]

OperationalRiskLevel = Literal[
    "low",
    "medium",
    "high",
    "critical",
]


@dataclass(frozen=True, slots=True)
class ShipmentOperationalIssue:
    code: str
    severity: OperationalSeverity
    message: str
    recommended_action: str
    age: timedelta | None = None


@dataclass(frozen=True, slots=True)
class ShipmentOperationalAnalysis:
    issues: tuple[ShipmentOperationalIssue, ...]

    @property
    def has_issues(self) -> bool:
        return bool(self.issues)

    @property
    def highest_severity(self) -> OperationalSeverity:
        if any(issue.severity == "critical" for issue in self.issues):
            return "critical"

        if any(issue.severity == "warning" for issue in self.issues):
            return "warning"

        return "info"

    @property
    def risk_score(self) -> int:
        weights: dict[OperationalSeverity, int] = {
            "info": 5,
            "warning": 25,
            "critical": 60,
        }

        return min(
            100,
            sum(weights[issue.severity] for issue in self.issues),
        )

    @property
    def risk_level(self) -> OperationalRiskLevel:
        if self.highest_severity == "critical":
            return "critical"

        if self.risk_score >= 50:
            return "high"

        if self.risk_score > 0:
            return "medium"

        return "low"
