"""Ordered cross-layer flow event log."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Iterable, Mapping

from .events import FlowEvent, now_timestamp
from .validation import validate_flow_event, validate_flow_event_sequence


@dataclass(frozen=True)
class FlowEventLog:
    run_id: str
    employee_id: str | None = None
    message_event_id: str | None = None
    status: str = "running"
    root_event_id: str | None = None
    events: tuple[FlowEvent, ...] = ()
    started_at: str = field(default_factory=now_timestamp)
    ended_at: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_events(
        cls,
        run_id: str,
        events: Iterable[FlowEvent],
        *,
        employee_id: str | None = None,
        message_event_id: str | None = None,
        status: str = "running",
        metadata: Mapping[str, Any] | None = None,
    ) -> "FlowEventLog":
        log = cls(
            run_id=run_id,
            employee_id=employee_id,
            message_event_id=message_event_id,
            status=status,
            metadata=metadata or {},
        )
        for event in events:
            log = log.append(event)
        return log

    def append(self, event: FlowEvent) -> "FlowEventLog":
        validate_flow_event(event)
        if event.run_id != self.run_id:
            raise ValueError("event run_id does not match log run_id")
        next_event = event
        if next_event.sequence is None:
            next_event = replace(next_event, sequence=len(self.events))
        next_events = (*self.events, next_event)
        validate_flow_event_sequence(list(next_events))
        root_id = self.root_event_id or next_event.id
        return replace(self, events=next_events, root_event_id=root_id)

    def finish(self, status: str = "completed") -> "FlowEventLog":
        return replace(self, status=status, ended_at=now_timestamp())

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "employee_id": self.employee_id,
            "message_event_id": self.message_event_id,
            "status": self.status,
            "root_event_id": self.root_event_id,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "metadata": dict(self.metadata),
            "events": [event.to_dict() for event in self.events],
        }


__all__ = ["FlowEventLog"]
