"""Reserved post-execution feedback contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from domain.core.ids import new_id


@dataclass(frozen=True)
class FeedbackSignal:
    feedback_id: str
    source: str
    severity: str
    affected_artifact: str
    finding: str
    recommendation: str
    status: str
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


def make_feedback_signal(
    *,
    source: str,
    severity: str,
    affected_artifact: str,
    finding: str,
    recommendation: str,
    status: str,
    feedback_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> FeedbackSignal:
    """Create the stable feedback contract from specialized feedback packages."""

    if metadata:
        finding = f"{finding} | metadata={metadata}"
    return FeedbackSignal(
        feedback_id=feedback_id or new_id("fb"),
        source=source,
        severity=severity,
        affected_artifact=affected_artifact,
        finding=finding,
        recommendation=recommendation,
        status=status,
    )


__all__ = ["FeedbackSignal", "make_feedback_signal"]
