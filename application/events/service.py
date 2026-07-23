"""Runtime service for registering event types and triggering instances."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Mapping, Sequence

from domain.core.ids import new_id
from domain.core.models import EventInstance, EventTypeDefinition
from domain.core.contracts import EventQueue, EventRegistry
from .security import EventSecurityPolicy


class EventService:
    """Coordinate event type registration and event instance triggering."""

    def __init__(
        self,
        registry: EventRegistry,
        queue: EventQueue,
        *,
        security_policy: EventSecurityPolicy | None = None,
    ) -> None:
        self._registry = registry
        self._queue = queue
        self._security_policy = security_policy or EventSecurityPolicy()

    def register_type(self, definition: EventTypeDefinition) -> None:
        self._registry.register(definition)

    def register_types(self, definitions: Sequence[EventTypeDefinition]) -> None:
        for definition in definitions:
            self.register_type(definition)

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
        definition = self._registry.get(type_id)
        if definition is None:
            raise KeyError(f"event type is not registered: {type_id}")

        security = self._security_policy.authorize(definition, payload or {}, actor_id=actor_id)
        if not security.allowed:
            raise PermissionError(f"event trigger denied for {type_id}: {security.reason}")

        now = datetime.now(timezone.utc).isoformat()
        event = EventInstance(
            id=new_id("evt"),
            type_id=type_id,
            trigger_type=definition.trigger_type,
            payload=security.payload,
            agent_id=agent_id,
            workspace_id=workspace_id,
            context_hint=context_hint,
            fire_at=fire_at,
            created_at=now,
            updated_at=now,
        )
        return self._queue.enqueue(event)
