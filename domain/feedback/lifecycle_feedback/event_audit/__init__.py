"""Feedback signals for event runtime acknowledgement and audit."""

from __future__ import annotations

from ...contracts import FeedbackSignal, make_feedback_signal


def feedback_from_event_audit(
    *,
    event_id: str,
    event_type: str,
    status: str,
    detail: str = "",
) -> FeedbackSignal:
    normalized = status.lower()
    severity = "info" if normalized in {"done", "acknowledged", "consumed"} else "warning"
    return make_feedback_signal(
        source="event_audit",
        severity=severity,
        affected_artifact=event_id,
        finding=f"Event {event_id} ({event_type}) audit status={normalized}.",
        recommendation=detail or _recommendation(normalized),
        status="pass" if severity == "info" else normalized,
        metadata={"event_id": event_id, "event_type": event_type, "event_status": normalized},
    )


def _recommendation(status: str) -> str:
    if status == "blocked":
        return "Keep the event available for investigation or retry."
    if status == "dead_letter":
        return "Move the event to a dead-letter review path."
    return "Persist the acknowledgement for traceability."


__all__ = ["feedback_from_event_audit"]
