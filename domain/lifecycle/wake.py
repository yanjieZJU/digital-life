"""Adapter-neutral wake session planning helpers."""

from __future__ import annotations

import uuid
from datetime import datetime


L4_TOOLSETS = ["actions", "senses", "trading", "web"]
L4_TASK_TOOLSETS = ["actions", "senses", "tasks", "web", "terminal", "trading"]


def enabled_toolsets_for_reason(reason: str) -> list[str]:
    if reason == "task_reminder":
        return L4_TASK_TOOLSETS
    return L4_TOOLSETS


def make_wake_session_id(reason: str, now: datetime | None = None) -> str:
    from domain.lifecycle import clock as _clock
    timestamp = (now or _clock.now_dt()).strftime("%m%d_%H%M")
    reason_slug = "".join(ch if ch.isalnum() else "_" for ch in reason.lower()).strip("_")
    reason_slug = reason_slug or "wake"
    return f"tx_{reason_slug}_{timestamp}_{uuid.uuid4().hex[:6]}"


def make_wake_session_log_filename(session_id: str) -> str:
    return f"{session_id}.json"


__all__ = [
    "L4_TASK_TOOLSETS",
    "L4_TOOLSETS",
    "enabled_toolsets_for_reason",
    "make_wake_session_id",
    "make_wake_session_log_filename",
]
