"""Validation rules for cross-layer flow events."""

from __future__ import annotations

from .events import FLOW_EVENT_LAYERS, FLOW_EVENT_SEVERITIES, FlowEvent


class FlowEventValidationError(ValueError):
    """Raised when a flow event violates the canonical contract."""


def validate_flow_event(event: FlowEvent) -> None:
    for field_name in ("id", "run_id", "type", "layer", "source", "timestamp"):
        if not str(getattr(event, field_name, "") or "").strip():
            raise FlowEventValidationError(f"{field_name} is required")
    if event.layer not in FLOW_EVENT_LAYERS:
        raise FlowEventValidationError(f"unknown flow event layer: {event.layer}")
    if event.severity not in FLOW_EVENT_SEVERITIES:
        raise FlowEventValidationError(f"unknown flow event severity: {event.severity}")
    if event.sequence is not None and event.sequence < 0:
        raise FlowEventValidationError("sequence must be non-negative")


def validate_flow_event_sequence(events: list[FlowEvent]) -> None:
    last_sequence: int | None = None
    for event in events:
        validate_flow_event(event)
        if event.sequence is None:
            continue
        if last_sequence is not None and event.sequence < last_sequence:
            raise FlowEventValidationError("event sequence moved backwards")
        last_sequence = event.sequence


def validate_flow_action_outcomes(events: list[FlowEvent]) -> None:
    """Validate completed execution traces have outcomes for dispatched actions."""

    outcome_keys: set[str] = set()
    for event in events:
        if event.type in {"ObservationReceivedEvent", "ToolErrorEvent", "ExecutionFailedEvent"}:
            outcome_keys.update(_link_keys(event))

    missing: list[str] = []
    for event in events:
        if event.type != "ActionDispatchedEvent":
            continue
        keys = _link_keys(event)
        if not keys or not any(key in outcome_keys for key in keys):
            missing.append(event.id)
    if missing:
        raise FlowEventValidationError(
            "action dispatch needs ObservationReceivedEvent, ToolErrorEvent, or ExecutionFailedEvent: "
            + ", ".join(missing)
        )


def _link_keys(event: FlowEvent) -> set[str]:
    keys = {event.causation_event_id} if event.causation_event_id else set()
    payload = dict(event.payload)
    execution_request = payload.get("execution_request")
    if isinstance(execution_request, dict):
        keys.add(str(execution_request.get("execution_id") or ""))
    for field_name in ("execution_id", "tool_call_id", "action_id"):
        keys.add(str(payload.get(field_name) or ""))
    return {key for key in keys if key}


__all__ = [
    "FlowEventValidationError",
    "validate_flow_action_outcomes",
    "validate_flow_event",
    "validate_flow_event_sequence",
]
