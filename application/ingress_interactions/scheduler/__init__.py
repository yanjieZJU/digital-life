"""Scheduler ingress interactions normalization."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ..contracts import InteractionMessage


class SchedulerIngress:
    """Convert scheduled triggers into InteractionMessage."""

    def normalize(
        self,
        *,
        job_id: str,
        trigger: str,
        payload: Mapping[str, Any] | None = None,
        fire_at: str | None = None,
    ) -> InteractionMessage:
        normalized_payload = dict(payload or {})
        content = str(normalized_payload.pop("text", "") or normalized_payload.pop("message", "") or trigger)
        normalized_payload.update({"external_channel": "scheduler", "job_id": job_id, "trigger": trigger})
        if fire_at:
            normalized_payload["fire_at"] = fire_at
        return InteractionMessage(
            message_id=f"scheduler:{job_id}:{trigger}",
            actor_id=job_id,
            content=content,
            metadata=normalized_payload,
            correlation_id=job_id,
        )


__all__ = ["SchedulerIngress"]
