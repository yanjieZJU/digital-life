"""Wake liveness evaluation for the stale-RUNNING recovery path.

The cron tick (``cron_lifecycle._run_l4_tick_inner``) and the process-startup
cleanup (``server._cleanup_stale_affair_on_startup``) both need to answer one
question when an affair is marked ``RUNNING``:

    *Is the wake behind this affair actually still doing useful work, or has it
    died without rolling back?*

The historical signal — ``affairs.updated_at`` freshness — is wrong for this
purpose: ``updated_at`` is refreshed only when the affair **changes state**, and
a wake sets ``RUNNING`` once at start (``scheduler.py``) and never touches the
row again while running. A legitimate 20-minute LLM task therefore looks
"stale" after 5 minutes, and the old hard-coded 300 s check rolled it back to
``BLOCKED`` — which in turn made ``_wake_or_inject`` dispatch a **new** wake
(instead of injecting mid-session) when fresh events arrived. That is the root
cause of the alpha "wake #1181 still running but #1182 fired" defect.

This module replaces that signal with two independent evidence sources and a
single shared threshold:

1. ``_wake_in_progress[instance_id]`` — the in-process module-level flag set in
   ``wake_digital_life`` while the wake holds the instance lock. Authoritative
   but **process-local**: invisible to other instance subprocesses and empty
   right after a restart.
2. ``RuntimeLogDB.last_turn_at()`` — the most recent ``turn`` row timestamp.
   The agent writes one or more turn rows per LLM call, so this is a fine-
   grained, durable "the model is still emitting" heartbeat that survives
   process restarts.

A wake is considered alive if *either* signal is recent enough. Only when both
say "dead" does the caller roll back the affair — and the threshold is shared
with the scheduler zombie-lock guard so the two never disagree.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any

logger = logging.getLogger(__name__)

# Stale-RUNNING threshold, shared by cron tick, startup cleanup and (logically)
# the scheduler zombie-lock guard so the three never drift into the old
# 300 s / 600 s mismatch that left a "dark window" where cron had already
# flipped the affair to BLOCKED but the old wake still held the instance lock.
#
# Default 1800 s (30 min): measured legitimate wake runs have exceeded 1296 s
# (alpha wake_seq 1155) and completed normally; 5 minutes was simply wrong.
STALE_RUNNING_SECONDS = float(
    os.environ.get("DIGITAL_LIFE_STALE_RUNNING_SECONDS", "1800")
)


def evaluate_wake_alive(
    instance_id: str,
    *,
    stale_threshold_s: float | None = None,
    now: float | None = None,
) -> tuple[bool, str, dict[str, Any]]:
    """Decide whether the currently-``RUNNING`` wake for ``instance_id`` is alive.

    Returns ``(was_alive, reason, signals)`` where ``signals`` captures the raw
    evidence for structured logging at every call site.

    Decision (strongest live signal wins):

    1. ``_wake_in_progress[instance_id]`` is set
       → alive. Fast in-process path; the wake thread is holding the lock.
    2. ``audit.last_turn_at()`` is within ``stale_threshold_s``
       → alive. Turn heartbeat says the model is still producing turns. This is
       the cross-process / post-restart fallback.
    3. No turn yet, but the most recent wake started within ``stale_threshold_s``
       → alive. Startup window: a brand-new wake has not landed its first turn.
    4. Otherwise → not alive. Caller may roll the affair back to ``BLOCKED``.

    ``stale_threshold_s`` defaults to :data:`STALE_RUNNING_SECONDS` so every
    caller uses the same knob. ``now`` is injectable for deterministic tests.
    """
    threshold = stale_threshold_s if stale_threshold_s is not None else STALE_RUNNING_SECONDS
    now_ts = now if now is not None else time.time()

    # --- Signal 1: in-process wake-in-progress flag -------------------------
    wake_in_progress = False
    try:
        from domain.lifecycle.scheduler import _is_wake_in_progress

        wake_in_progress = bool(_is_wake_in_progress(instance_id))
    except Exception as exc:  # defensive: must never crash the cron tick
        logger.debug("evaluate_wake_alive: _is_wake_in_progress lookup failed: %s", exc)
    if wake_in_progress:
        return True, "wake_in_progress", {"wake_in_progress": True, "threshold_s": threshold}

    # --- Signal 2 / 3: durable turn / wake-start heartbeat ------------------
    last_turn: float | None = None
    last_wake_start: float | None = None
    try:
        from infrastructure.persistence.instance import get_audit

        audit = get_audit(instance_id)
        last_turn = audit.last_turn_at()
        last_wake_start = audit.last_wake_started_at()
    except Exception as exc:
        logger.debug("evaluate_wake_alive: audit heartbeat lookup failed: %s", exc)

    if last_turn is not None:
        turn_age = now_ts - last_turn
        if turn_age <= threshold:
            return True, "turn_heartbeat", {
                "wake_in_progress": False,
                "last_turn_at": last_turn,
                "turn_age_s": round(turn_age, 1),
                "threshold_s": threshold,
            }
        # turn exists but stale → fall through to "dead"
        return (
            False,
            "turn_stale",
            {
                "wake_in_progress": False,
                "last_turn_at": last_turn,
                "turn_age_s": round(turn_age, 1),
                "threshold_s": threshold,
            },
        )

    # No turn row at all: only treat as alive if a wake just started.
    if last_wake_start is not None:
        start_age = now_ts - last_wake_start
        if start_age <= threshold:
            return True, "wake_just_started", {
                "wake_in_progress": False,
                "last_turn_at": None,
                "last_wake_started_at": last_wake_start,
                "start_age_s": round(start_age, 1),
                "threshold_s": threshold,
            }
        return (
            False,
            "wake_started_but_no_turn",
            {
                "wake_in_progress": False,
                "last_turn_at": None,
                "last_wake_started_at": last_wake_start,
                "start_age_s": round(start_age, 1),
                "threshold_s": threshold,
            },
        )

    return False, "no_evidence", {
        "wake_in_progress": False,
        "last_turn_at": None,
        "last_wake_started_at": None,
        "threshold_s": threshold,
    }


__all__ = ["STALE_RUNNING_SECONDS", "evaluate_wake_alive"]
