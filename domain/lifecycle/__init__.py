"""Digital-life lifecycle execution capability."""

from .affairs import Affair, WaitIntent, normalize_affair_update_fields
from .clock import BEIJING, humanize_delta, now_dt, now_iso, parse_iso, ts_prefix
from .runtime_context import get_current_affair, set_current_affair
from .state_machine import AffairStatus, LifecycleState, WaitType, WakeReason
from .routine_scheduler import (
    ensure_routine_events,
    get_quiet_hours,
    load_routines,
    save_routines,
)
from .session_events import consume_signalled_events, signal_new_events

__all__ = [
    "Affair",
    "AffairStatus",
    "BEIJING",
    "consume_signalled_events",
    "ensure_routine_events",
    "get_current_affair",
    "get_quiet_hours",
    "humanize_delta",
    "LifecycleState",
    "load_routines",
    "normalize_affair_update_fields",
    "now_dt",
    "now_iso",
    "parse_iso",
    "save_routines",
    "set_current_affair",
    "signal_new_events",
    "ts_prefix",
    "WaitIntent",
    "WakeReason",
    "WaitType",
]
