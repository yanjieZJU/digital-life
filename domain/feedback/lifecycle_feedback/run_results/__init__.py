"""Feedback signals derived from runtime execution results."""

from __future__ import annotations

from typing import Any, Mapping

from ...contracts import FeedbackSignal, make_feedback_signal


def feedback_from_runtime_result(
    result: object,
    *,
    affected_artifact: str | None = None,
) -> FeedbackSignal:
    execution_id = str(_field(result, "execution_id", "execution"))
    status = str(_field(result, "status", "unknown")).lower()
    error = str(_field(result, "error", ""))
    severity = _severity_for_status(status)
    return make_feedback_signal(
        source="runtime_result",
        severity=severity,
        affected_artifact=affected_artifact or execution_id,
        finding=f"Runtime execution {execution_id} finished with status={status}.",
        recommendation=_recommendation_for_status(status, error),
        status=_feedback_status(status),
        metadata={"execution_id": execution_id, "runtime_status": status, "error": error} if error else None,
    )


def feedback_from_runtime_failure(
    *,
    execution_id: str,
    error: str,
    affected_artifact: str | None = None,
) -> FeedbackSignal:
    return make_feedback_signal(
        source="runtime_result",
        severity="error",
        affected_artifact=affected_artifact or execution_id,
        finding=f"Runtime execution {execution_id} failed.",
        recommendation=error or "Inspect execution trace and retry after the blocker is removed.",
        status="fail",
        metadata={"execution_id": execution_id, "error": error},
    )


def feedback_from_blocked_execution(
    *,
    execution_id: str,
    blocker: str,
    affected_artifact: str | None = None,
) -> FeedbackSignal:
    return make_feedback_signal(
        source="runtime_result",
        severity="warning",
        affected_artifact=affected_artifact or execution_id,
        finding=f"Runtime execution {execution_id} is blocked.",
        recommendation=blocker or "Resolve the blocker before continuing this execution.",
        status="blocked",
        metadata={"execution_id": execution_id, "blocker": blocker},
    )


def _field(result: object, name: str, default: Any = "") -> Any:
    if isinstance(result, Mapping):
        return result.get(name, default)
    return getattr(result, name, default)


def _severity_for_status(status: str) -> str:
    if status in {"failed", "error", "rejected", "cancelled"}:
        return "error"
    if status in {"blocked", "partial", "stuck"}:
        return "warning"
    return "info"


def _feedback_status(status: str) -> str:
    if status in {"completed", "done", "accepted", "running"}:
        return "pass"
    if status in {"blocked", "partial", "stuck"}:
        return "blocked"
    return "fail"


def _recommendation_for_status(status: str, error: str) -> str:
    if error:
        return error
    if status in {"blocked", "partial", "stuck"}:
        return "Surface the blocker to the feedback channel and keep the execution resumable."
    if status in {"failed", "error", "rejected", "cancelled"}:
        return "Inspect execution events and retry after correcting the failure cause."
    return "Record the result and proceed to the next executable step."


__all__ = [
    "feedback_from_blocked_execution",
    "feedback_from_runtime_failure",
    "feedback_from_runtime_result",
]
