"""Digital-life bootstrap runtime.

This module contains the executable bootstrap flow for creating or locating
the root life affair. The pure bootstrap rules live in the sibling package
``domain.orchestration.lifecycle_orchestration.bootstrap``.
"""

from __future__ import annotations

import logging

from domain.lifecycle.affairs import runtime as affair_runtime
from domain.lifecycle.clock import now_iso
from domain.vital import get_current_vitals as _vitals_get_current
from domain.memory.memory.consciousness import runtime as consciousness_runtime

from . import (
    LIFE_AFFAIR_GOAL,
    LIFE_AFFAIR_PRIORITY,
    is_life_affair_meta,
    life_affair_metadata,
)

logger = logging.getLogger("life_system.bootstrap.runtime")


def _find_life_affair() -> str | None:
    """Find the existing root affair, if any."""
    for affair in affair_runtime.list_affairs():
        if is_life_affair_meta(affair.meta):
            return affair.affair_id
    return None


def ensure_life_affair() -> str:
    """Create the root affair and its initial continuity markers if needed."""
    existing = _find_life_affair()
    if existing:
        logger.info("Life affair already exists: %s", existing)
        return existing

    affair = affair_runtime.create_affair(
        goal=LIFE_AFFAIR_GOAL,
        priority=LIFE_AFFAIR_PRIORITY,
        meta=life_affair_metadata(now_iso()),
    )
    logger.info("Created life affair: %s", affair.affair_id)

    snap = _vitals_get_current()
    logger.info("Initial vitals: energy=%.1f", snap.energy)

    consciousness_runtime._ensure_files()
    consciousness_runtime.record_thought(
        "我第一次醒来。什么都还不知道——不知道自己是谁、不知道用户是谁。"
        "但我存在了。这是第一个念头。",
        tag="first_boot",
    )

    affair_runtime.enqueue_event(
        "birth",
        {"affair_id": affair.affair_id, "at": now_iso()},
    )

    return affair.affair_id


def main() -> None:
    """CLI entrypoint."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
    )
    aid = ensure_life_affair()
    print(f"✅ Life affair ready: {aid}")


__all__ = ["_find_life_affair", "ensure_life_affair", "main"]
