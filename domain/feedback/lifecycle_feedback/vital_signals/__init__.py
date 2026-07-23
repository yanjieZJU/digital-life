"""Feedback signals for vital threshold crossings."""

from __future__ import annotations

from ...contracts import FeedbackSignal, make_feedback_signal


def feedback_from_vital_signal(
    *,
    dimension: str,
    value: float,
    threshold: float,
    direction: str = "below",
) -> FeedbackSignal:
    breached = value < threshold if direction == "below" else value > threshold
    return make_feedback_signal(
        source="vital_signal",
        severity="warning" if breached else "info",
        affected_artifact=dimension,
        finding=f"Vital {dimension} value={value} threshold={threshold} direction={direction}.",
        recommendation="Trigger a short proactive status report if this degradation can affect behavior."
        if breached
        else "No action required.",
        status="threshold_breached" if breached else "pass",
        metadata={"dimension": dimension, "value": value, "threshold": threshold, "direction": direction},
    )


__all__ = ["feedback_from_vital_signal"]
