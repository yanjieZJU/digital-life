"""Feedback signals derived from completed execution sessions."""

from __future__ import annotations

from ...contracts import FeedbackSignal, make_feedback_signal


def feedback_from_session_summary(
    *,
    session_id: str,
    status: str,
    summary: str = "",
    tool_call_count: int = 0,
) -> FeedbackSignal:
    normalized = status.lower()
    failed = normalized not in {"done", "completed", "pass"}
    return make_feedback_signal(
        source="session_feedback",
        severity="warning" if failed else "info",
        affected_artifact=session_id,
        finding=f"Session {session_id} completed with status={normalized}.",
        recommendation=summary or "Consolidate the session trace into memory if it contains durable context.",
        status="fail" if failed else "pass",
        metadata={"session_id": session_id, "tool_call_count": tool_call_count},
    )


def feedback_from_proactive_report(
    *,
    session_id: str,
    message: str,
    reason: str,
) -> FeedbackSignal:
    return make_feedback_signal(
        source="session_feedback",
        severity="info",
        affected_artifact=session_id,
        finding=f"Proactive report emitted for session {session_id}.",
        recommendation=message,
        status="reported",
        metadata={"session_id": session_id, "reason": reason},
    )


__all__ = ["feedback_from_proactive_report", "feedback_from_session_summary"]
