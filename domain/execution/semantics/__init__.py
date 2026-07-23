"""Execution Semantics domain capability."""

from .contracts import ExecutionRequest, ExecutionState
from .event_log import EventLog
from .event_validation import EventValidationError, sanitize_display_payload, validate_event_sequence, validate_execution_event
from .events import (
    ActionEvent,
    AgentErrorEvent,
    CANONICAL_EVENT_TYPES,
    Condensation,
    CondensationRequest,
    ExecutionEvent,
    MessageTraceEvent,
    ObservationEvent,
    RejectionEvent,
    StateUpdateEvent,
)
from .runtime_ports import ExecutionEngineEventAdapter, RuntimeEnginePort, RuntimeExecutionResult


def get_vitals_engine():
    """Return the vitals simulation engine without creating import cycles."""
    from domain.vital.simulation import get_engine
    return get_engine()

__all__ = [
    "ExecutionRequest",
    "ExecutionState",
    "ActionEvent",
    "AgentErrorEvent",
    "CANONICAL_EVENT_TYPES",
    "Condensation",
    "CondensationRequest",
    "EventLog",
    "EventValidationError",
    "ExecutionEngineEventAdapter",
    "ExecutionEvent",
    "MessageTraceEvent",
    "ObservationEvent",
    "RejectionEvent",
    "StateUpdateEvent",
    "RuntimeEnginePort",
    "RuntimeExecutionResult",
    "get_vitals_engine",
    "sanitize_display_payload",
    "validate_event_sequence",
    "validate_execution_event",
]
