"""Wakeup and retry policy rules for lifecycle orchestration."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional


def choose_auto_rest_wake_time(now: datetime, *, daytime_sleep_hours: float = 2.0) -> datetime:
    """Choose the next wake time when the agent exits without calling rest."""
    hour = now.hour
    if hour >= 22:
        return now.replace(hour=7, minute=0, second=0, microsecond=0) + timedelta(days=1)
    if hour < 5:
        return now.replace(hour=7, minute=0, second=0, microsecond=0)
    return now + timedelta(hours=daytime_sleep_hours)


def next_retry_delay_minutes(previous_resume_when: Optional[str], previous_set_at: Optional[str]) -> int:
    """Exponential retry backoff in minutes, capped at one hour."""
    base_delay = 5
    if previous_resume_when and previous_set_at:
        try:
            previous_time = datetime.fromisoformat(previous_resume_when)
            previous_set = datetime.fromisoformat(previous_set_at)
            previous_delay = abs((previous_time - previous_set).total_seconds()) / 60
            base_delay = min(int(previous_delay * 2), 60)
        except Exception:
            pass
    return base_delay


def retry_intent_meta(now: datetime) -> dict:
    return {
        "set_at": now.isoformat(timespec="seconds"),
        "cooldown": True,
    }


__all__ = ["choose_auto_rest_wake_time", "next_retry_delay_minutes", "retry_intent_meta"]
