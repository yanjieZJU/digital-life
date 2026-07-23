"""Ports for flow event recording and persistence."""

from __future__ import annotations

from typing import Protocol

from .event_log import FlowEventLog
from .events import FlowEvent


class EventLogRepositoryPort(Protocol):
    def start_log(self, log: FlowEventLog) -> FlowEventLog: ...

    def append_event(self, event: FlowEvent) -> FlowEvent: ...

    def finish_log(self, run_id: str, *, status: str) -> None: ...

    def get(self, run_id: str) -> FlowEventLog | None: ...


class EventRecorderPort(Protocol):
    def record(self, event: FlowEvent) -> FlowEvent: ...

    def finish(self, run_id: str, *, status: str) -> None: ...


__all__ = ["EventLogRepositoryPort", "EventRecorderPort"]
