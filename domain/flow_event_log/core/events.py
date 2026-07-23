"""Cross-layer flow events for observable digital employee runs."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping
from uuid import uuid4


FLOW_EVENT_LAYERS = {"ingress", "memory", "orchestration", "execution", "feedback"}
FLOW_EVENT_SEVERITIES = {"debug", "info", "warning", "error"}


def new_flow_event_id() -> str:
    return f"flow_evt_{uuid4().hex}"


def now_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True, kw_only=True)
class FlowEvent:
    """A single observable transition in a run.

    The event references business objects by id. It does not replace objects
    such as MessageEvent, OrchestrationPlan, ExecutionRequest, or FeedbackSignal.
    """

    run_id: str
    source: str
    id: str = field(default_factory=new_flow_event_id)
    sequence: int | None = None
    type: str = "FlowEvent"
    layer: str = "execution"
    timestamp: str = field(default_factory=now_timestamp)
    employee_id: str | None = None
    message_event_id: str | None = None
    parent_event_id: str | None = None
    causation_event_id: str | None = None
    correlation_id: str | None = None
    payload: Mapping[str, Any] = field(default_factory=dict)
    summary: str = ""
    severity: str = "info"

    def to_dict(self) -> dict[str, Any]:
        result = {
            "id": self.id,
            "run_id": self.run_id,
            "sequence": self.sequence,
            "type": self.type,
            "layer": self.layer,
            "source": self.source,
            "timestamp": self.timestamp,
            "employee_id": self.employee_id,
            "message_event_id": self.message_event_id,
            "parent_event_id": self.parent_event_id,
            "causation_event_id": self.causation_event_id,
            "correlation_id": self.correlation_id,
            "payload": dict(self.payload),
            "summary": self.summary,
            "severity": self.severity,
        }
        return {key: value for key, value in result.items() if value is not None}


def flow_event_from_dict(data: Mapping[str, Any]) -> FlowEvent:
    """Restore a persisted event without requiring a concrete subclass."""

    return FlowEvent(
        id=str(data["id"]),
        run_id=str(data["run_id"]),
        sequence=_int_or_none(data.get("sequence")),
        type=str(data["type"]),
        layer=str(data["layer"]),
        source=str(data["source"]),
        timestamp=str(data["timestamp"]),
        employee_id=_optional_text(data.get("employee_id")),
        message_event_id=_optional_text(data.get("message_event_id")),
        parent_event_id=_optional_text(data.get("parent_event_id")),
        causation_event_id=_optional_text(data.get("causation_event_id")),
        correlation_id=_optional_text(data.get("correlation_id")),
        payload=data.get("payload") if isinstance(data.get("payload"), Mapping) else {},
        summary=str(data.get("summary") or ""),
        severity=str(data.get("severity") or "info"),
    )


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text or None


def _int_or_none(value: object) -> int | None:
    if value is None:
        return None
    return int(value)


__all__ = [
    "FLOW_EVENT_LAYERS",
    "FLOW_EVENT_SEVERITIES",
    "FlowEvent",
    "flow_event_from_dict",
    "new_flow_event_id",
    "now_timestamp",
]
