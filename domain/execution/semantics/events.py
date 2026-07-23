"""Canonical execution trace events.

These events describe project-owned execution semantics. Runtime engines such
as Hermes translate into this contract through adapters; they do not define the
canonical shape.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence
from uuid import uuid4


def new_event_id() -> str:
    return f"evt_{uuid4().hex}"


def now_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True, kw_only=True)
class ExecutionEvent:
    source: str
    run_id: str
    id: str = field(default_factory=new_event_id)
    timestamp: str = field(default_factory=now_timestamp)
    employee_id: str | None = None
    workspace_id: str | None = None
    parent_event_id: str | None = None
    sequence: int | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    engine: str | None = None
    engine_event_id: str | None = None
    type: str = field(default="ExecutionEvent", init=False)

    def to_dict(self) -> dict[str, Any]:
        result = {
            "id": self.id,
            "type": self.type,
            "source": self.source,
            "timestamp": self.timestamp,
            "run_id": self.run_id,
            "employee_id": self.employee_id,
            "workspace_id": self.workspace_id,
            "parent_event_id": self.parent_event_id,
            "sequence": self.sequence,
            "metadata": dict(self.metadata),
            "engine": self.engine,
            "engine_event_id": self.engine_event_id,
        }
        return {key: value for key, value in result.items() if value is not None}


@dataclass(frozen=True, kw_only=True)
class MessageTraceEvent(ExecutionEvent):
    message_id: str
    role: str
    content: str
    sender: str | None = None
    type: str = field(default="MessageTraceEvent", init=False)

    def to_dict(self) -> dict[str, Any]:
        result = super().to_dict()
        result.update({
            "message_id": self.message_id,
            "role": self.role,
            "content": self.content,
            "sender": self.sender,
        })
        return {key: value for key, value in result.items() if value is not None}


@dataclass(frozen=True, kw_only=True)
class ActionEvent(ExecutionEvent):
    tool_call_id: str
    tool_name: str
    summary: str = ""
    security_risk: str = "UNKNOWN"
    action: Mapping[str, Any] = field(default_factory=dict)
    thought: Sequence[Mapping[str, Any]] = field(default_factory=tuple)
    type: str = field(default="ActionEvent", init=False)

    def to_dict(self) -> dict[str, Any]:
        result = super().to_dict()
        result.update({
            "tool_call_id": self.tool_call_id,
            "tool_name": self.tool_name,
            "summary": self.summary,
            "security_risk": self.security_risk,
            "action": dict(self.action),
            "thought": list(self.thought),
        })
        return result


@dataclass(frozen=True, kw_only=True)
class ObservationEvent(ExecutionEvent):
    tool_call_id: str
    tool_name: str
    action_id: str | None = None
    status: str = "succeeded"
    observation: Mapping[str, Any] = field(default_factory=dict)
    type: str = field(default="ObservationEvent", init=False)

    def to_dict(self) -> dict[str, Any]:
        result = super().to_dict()
        result.update({
            "action_id": self.action_id,
            "tool_call_id": self.tool_call_id,
            "tool_name": self.tool_name,
            "status": self.status,
            "observation": dict(self.observation),
        })
        return {key: value for key, value in result.items() if value is not None}


@dataclass(frozen=True, kw_only=True)
class AgentErrorEvent(ExecutionEvent):
    message: str
    error_kind: str = "unknown"
    tool_call_id: str | None = None
    tool_name: str | None = None
    recoverable: bool = False
    type: str = field(default="AgentErrorEvent", init=False)

    def to_dict(self) -> dict[str, Any]:
        result = super().to_dict()
        result.update({
            "error_kind": self.error_kind,
            "message": self.message,
            "tool_call_id": self.tool_call_id,
            "tool_name": self.tool_name,
            "recoverable": self.recoverable,
        })
        return {key: value for key, value in result.items() if value is not None}


@dataclass(frozen=True, kw_only=True)
class RejectionEvent(ExecutionEvent):
    action_id: str
    rejection_source: str
    tool_call_id: str | None = None
    tool_name: str | None = None
    rejection_reason: str = ""
    type: str = field(default="RejectionEvent", init=False)

    def to_dict(self) -> dict[str, Any]:
        result = super().to_dict()
        result.update({
            "action_id": self.action_id,
            "tool_call_id": self.tool_call_id,
            "tool_name": self.tool_name,
            "rejection_source": self.rejection_source,
            "rejection_reason": self.rejection_reason,
        })
        return {key: value for key, value in result.items() if value is not None}


@dataclass(frozen=True, kw_only=True)
class StateUpdateEvent(ExecutionEvent):
    state: str
    previous_state: str | None = None
    reason: str = ""
    type: str = field(default="StateUpdateEvent", init=False)

    def to_dict(self) -> dict[str, Any]:
        result = super().to_dict()
        result.update({
            "previous_state": self.previous_state,
            "state": self.state,
            "reason": self.reason,
        })
        return {key: value for key, value in result.items() if value is not None}


@dataclass(frozen=True, kw_only=True)
class CondensationRequest(ExecutionEvent):
    target_event_ids: Sequence[str] = field(default_factory=tuple)
    sequence_boundary: int | None = None
    reason: str = ""
    type: str = field(default="CondensationRequest", init=False)

    def to_dict(self) -> dict[str, Any]:
        result = super().to_dict()
        result.update({
            "target_event_ids": list(self.target_event_ids),
            "sequence_boundary": self.sequence_boundary,
            "reason": self.reason,
        })
        return {key: value for key, value in result.items() if value is not None}


@dataclass(frozen=True, kw_only=True)
class Condensation(ExecutionEvent):
    summary: str
    forgotten_event_ids: Sequence[str] = field(default_factory=tuple)
    summary_offset: int = 0
    llm_response_id: str | None = None
    type: str = field(default="Condensation", init=False)

    def to_dict(self) -> dict[str, Any]:
        result = super().to_dict()
        result.update({
            "forgotten_event_ids": list(self.forgotten_event_ids),
            "summary": self.summary,
            "summary_offset": self.summary_offset,
            "llm_response_id": self.llm_response_id,
        })
        return {key: value for key, value in result.items() if value is not None}


CanonicalExecutionEvent = (
    MessageTraceEvent
    | ActionEvent
    | ObservationEvent
    | AgentErrorEvent
    | RejectionEvent
    | StateUpdateEvent
    | CondensationRequest
    | Condensation
)

CANONICAL_EVENT_TYPES = {
    "MessageTraceEvent",
    "ActionEvent",
    "ObservationEvent",
    "AgentErrorEvent",
    "RejectionEvent",
    "StateUpdateEvent",
    "CondensationRequest",
    "Condensation",
}


__all__ = [
    "ActionEvent",
    "AgentErrorEvent",
    "CANONICAL_EVENT_TYPES",
    "CanonicalExecutionEvent",
    "Condensation",
    "CondensationRequest",
    "ExecutionEvent",
    "MessageTraceEvent",
    "ObservationEvent",
    "RejectionEvent",
    "StateUpdateEvent",
    "new_event_id",
    "now_timestamp",
]
