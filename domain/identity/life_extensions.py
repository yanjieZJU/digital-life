"""Digital Life runtime extensions (loaded via env var providers)."""

from __future__ import annotations

from domain.lifecycle import clock as timezone


def message_prefix() -> str:
    return timezone.ts_prefix()


def system_prompt() -> str:
    # L4_LIFECYCLE_PROMPT + persona is injected via ephemeral_system_prompt
    # in the scheduler, not here. Returning empty avoids duplicate injection.
    return ""
