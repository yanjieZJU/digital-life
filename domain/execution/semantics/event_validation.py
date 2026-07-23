"""Validation and display-safety helpers for execution events."""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Mapping

from .events import (
    CANONICAL_EVENT_TYPES,
    ActionEvent,
    AgentErrorEvent,
    CanonicalExecutionEvent,
    Condensation,
    CondensationRequest,
    ExecutionEvent,
    ObservationEvent,
    RejectionEvent,
    StateUpdateEvent,
)

DISPLAY_MAX_TEXT = 4000
SECRET_KEYS = {"token", "secret", "password", "api_key", "authorization", "access_token", "refresh_token"}


class EventValidationError(ValueError):
    """Raised when an execution event violates the canonical contract."""


def validate_execution_event(event: ExecutionEvent) -> None:
    if event.type not in CANONICAL_EVENT_TYPES and event.type != "ExecutionEvent":
        raise EventValidationError(f"unknown execution event type: {event.type}")
    for field_name in ("id", "source", "timestamp", "run_id"):
        if not str(getattr(event, field_name, "") or "").strip():
            raise EventValidationError(f"{field_name} is required")
    if event.sequence is not None and event.sequence < 0:
        raise EventValidationError("sequence must be non-negative")
    if isinstance(event, ActionEvent):
        _require(event.tool_call_id, "tool_call_id")
        _require(event.tool_name, "tool_name")
        if event.security_risk not in {"LOW", "MEDIUM", "HIGH", "UNKNOWN"}:
            raise EventValidationError("security_risk must be LOW, MEDIUM, HIGH, or UNKNOWN")
    if isinstance(event, ObservationEvent):
        _require(event.tool_call_id, "tool_call_id")
        _require(event.tool_name, "tool_name")
        if event.status not in {"succeeded", "failed", "partial", "unlinked"}:
            raise EventValidationError("observation status is invalid")
        if not event.action_id and event.status != "unlinked":
            raise EventValidationError("unlinked observation must use status='unlinked'")
    if isinstance(event, AgentErrorEvent):
        if event.error_kind not in {"agent", "tool", "policy", "runtime", "unknown"}:
            raise EventValidationError("error_kind is invalid")
        _require(event.message, "message")
    if isinstance(event, RejectionEvent):
        _require(event.action_id, "action_id")
        if event.rejection_source not in {"human", "policy"}:
            raise EventValidationError("rejection_source must be human or policy")
    if isinstance(event, StateUpdateEvent):
        if event.state not in {"waiting_for_confirmation", "running", "paused", "finished", "failed", "stuck"}:
            raise EventValidationError("state is invalid")
    if isinstance(event, CondensationRequest):
        if not event.target_event_ids and event.sequence_boundary is None:
            raise EventValidationError("condensation request needs event ids or sequence boundary")
    if isinstance(event, Condensation):
        _require(event.summary, "summary")
        if not event.forgotten_event_ids and event.summary_offset <= 0:
            raise EventValidationError("condensation needs forgotten event ids or summary_offset")


def validate_event_sequence(events: list[ExecutionEvent]) -> None:
    last_sequence: int | None = None
    action_ids = {event.id for event in events if isinstance(event, ActionEvent)}
    for event in events:
        validate_execution_event(event)
        if event.sequence is not None:
            if last_sequence is not None and event.sequence < last_sequence:
                raise EventValidationError("event sequence moved backwards")
            last_sequence = event.sequence
        if isinstance(event, ObservationEvent) and event.action_id and event.action_id not in action_ids:
            raise EventValidationError(f"observation links to unknown action: {event.action_id}")


def sanitize_display_payload(value: Any, *, max_text: int = DISPLAY_MAX_TEXT) -> Any:
    if isinstance(value, Mapping):
        sanitized: dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key)
            if key_text.lower() in SECRET_KEYS:
                sanitized[key_text] = "[REDACTED]"
            else:
                sanitized[key_text] = sanitize_display_payload(item, max_text=max_text)
        return sanitized
    if isinstance(value, list):
        return [sanitize_display_payload(item, max_text=max_text) for item in value]
    if isinstance(value, tuple):
        return [sanitize_display_payload(item, max_text=max_text) for item in value]
    if isinstance(value, str):
        return value if len(value) <= max_text else value[:max_text] + "..."
    return value


def with_display_safe_payload(event: CanonicalExecutionEvent) -> CanonicalExecutionEvent:
    if isinstance(event, ActionEvent):
        return replace(event, action=sanitize_display_payload(event.action))
    if isinstance(event, ObservationEvent):
        return replace(event, observation=sanitize_display_payload(event.observation))
    if isinstance(event, AgentErrorEvent):
        return replace(event, message=str(sanitize_display_payload(event.message)))
    return event


def _require(value: object, field_name: str) -> None:
    if not str(value or "").strip():
        raise EventValidationError(f"{field_name} is required")


__all__ = [
    "DISPLAY_MAX_TEXT",
    "EventValidationError",
    "sanitize_display_payload",
    "validate_event_sequence",
    "validate_execution_event",
    "with_display_safe_payload",
]
