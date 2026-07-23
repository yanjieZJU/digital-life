"""Small application-facing recorder for flow events."""

from __future__ import annotations

from dataclasses import dataclass

from .event_log import FlowEventLog
from .events import FlowEvent
from .ports import EventLogRepositoryPort


@dataclass
class EventRecorder:
    repository: EventLogRepositoryPort

    def start(self, log: FlowEventLog) -> FlowEventLog:
        return self.repository.start_log(log)

    def record(self, event: FlowEvent) -> FlowEvent:
        return self.repository.append_event(event)

    def finish(self, run_id: str, *, status: str) -> None:
        self.repository.finish_log(run_id, status=status)

    def get(self, run_id: str) -> FlowEventLog | None:
        return self.repository.get(run_id)


__all__ = ["EventRecorder"]
