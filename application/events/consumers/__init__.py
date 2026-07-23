"""Event consumer coordination boundary."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping

from domain.core.contracts import EventQueue
from domain.core.models import EventInstance


EventHandler = Callable[[EventInstance], Mapping[str, Any] | bool | None]


@dataclass(frozen=True)
class EventConsumptionResult:
    status: str
    event_id: str = ""
    output: Mapping[str, Any] = field(default_factory=dict)
    error: str = ""


class EventConsumer:
    """Claim one queued event, run a handler, and acknowledge the outcome."""

    def __init__(self, queue: EventQueue, handler: EventHandler) -> None:
        self._queue = queue
        self._handler = handler

    def consume_next(self, *, agent_id: str | None = None) -> EventConsumptionResult:
        event = self._queue.next_pending(agent_id)
        if event is None:
            return EventConsumptionResult(status="idle")

        try:
            output = self._handler(event)
        except Exception as exc:
            self._mark_blocked(event.id)
            return EventConsumptionResult(status="blocked", event_id=event.id, error=str(exc))

        if output is False:
            self._mark_blocked(event.id)
            return EventConsumptionResult(status="blocked", event_id=event.id)

        self._queue.mark_done(event.id)
        return EventConsumptionResult(
            status="done",
            event_id=event.id,
            output=output if isinstance(output, Mapping) else {},
        )

    def _mark_blocked(self, event_id: str) -> None:
        marker = getattr(self._queue, "mark_blocked", None)
        if marker is None:
            self._queue.mark_done(event_id)
            return
        marker(event_id)


__all__ = ["EventConsumer", "EventConsumptionResult", "EventHandler"]
