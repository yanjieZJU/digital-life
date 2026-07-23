"""Domain task runtime wiring."""

from __future__ import annotations

from domain.lifecycle import clock as timezone
from domain.vital import consume_energy as vitals_consume_energy
from domain.lifecycle.events import emit_event, pop_due_events, consume_event
from domain.lifecycle.alarms import set_alarm, cancel_alarms_by_filter
from infrastructure.persistence.session_evidence import HermesSessionEvidenceReader
from domain.todos import configure_runtime_hooks


def configure_task_runtime() -> None:
    configure_runtime_hooks(
        now_iso=timezone.now_iso,
        parse_iso=timezone.parse_iso,
        now_dt=timezone.now_dt,
        emit_event=emit_event,
        set_alarm=set_alarm,
        cancel_alarms_by_filter=cancel_alarms_by_filter,
        pop_due_events=pop_due_events,
        consume_event=consume_event,
        consume_energy=vitals_consume_energy,
        session_evidence=HermesSessionEvidenceReader(),
    )


__all__ = ["configure_task_runtime"]
