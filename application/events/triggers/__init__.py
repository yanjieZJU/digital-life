"""Event trigger coordination boundary for the event runtime.

This package promotes scheduler, webhook, or channel signals into queued
runtime events. MessageEvent normalization remains in backend.ingress_interactions.
"""

from __future__ import annotations

from typing import Mapping

from application.events.service import EventService
from domain.core.models import EventInstance


class EventTriggerRouter:
    """Route scheduler, webhook, or channel signals into queued event instances."""

    def __init__(self, service: EventService) -> None:
        self._service = service

    def trigger(
        self,
        type_id: str,
        payload: Mapping[str, object] | None = None,
        *,
        agent_id: str | None = None,
        workspace_id: str | None = None,
        context_hint: str = "",
        fire_at: str | None = None,
        actor_id: str | None = None,
    ) -> EventInstance:
        return self._service.trigger(
            type_id,
            payload,
            agent_id=agent_id,
            workspace_id=workspace_id,
            context_hint=context_hint,
            fire_at=fire_at,
            actor_id=actor_id,
        )


__all__ = ["EventTriggerRouter"]
