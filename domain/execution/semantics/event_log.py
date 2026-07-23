"""Ordered execution event log."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Iterable

from .event_validation import validate_event_sequence, validate_execution_event
from .events import CanonicalExecutionEvent, now_timestamp


@dataclass(frozen=True)
class EventLog:
    run_id: str
    employee_id: str | None = None
    engine: str | None = None
    events: tuple[CanonicalExecutionEvent, ...] = ()
    created_at: str = field(default_factory=now_timestamp)
    updated_at: str = field(default_factory=now_timestamp)

    @classmethod
    def from_events(
        cls,
        run_id: str,
        events: Iterable[CanonicalExecutionEvent],
        *,
        employee_id: str | None = None,
        engine: str | None = None,
    ) -> "EventLog":
        log = cls(run_id=run_id, employee_id=employee_id, engine=engine)
        for event in events:
            log = log.append(event)
        return log

    def append(self, event: CanonicalExecutionEvent) -> "EventLog":
        validate_execution_event(event)
        sequence = event.sequence
        if sequence is None:
            sequence = len(self.events)
            event = replace(event, sequence=sequence)
        if self.events:
            previous = self.events[-1].sequence
            if previous is not None and sequence < previous:
                raise ValueError("event sequence moved backwards")
        next_events = (*self.events, event)
        validate_event_sequence(list(next_events))
        return replace(self, events=next_events, updated_at=event.timestamp)

    def to_dict(self) -> dict[str, object]:
        return {
            "run_id": self.run_id,
            "employee_id": self.employee_id,
            "engine": self.engine,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "events": [event.to_dict() for event in self.events],
        }


__all__ = ["EventLog"]
