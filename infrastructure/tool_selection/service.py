"""Tool selection service."""

from __future__ import annotations

from domain.core.contracts import ToolRegistry
from domain.core.models import EventTypeDefinition, ToolDefinition


class ToolSelectionService:
    """Select the tools allowed by an event type definition."""

    def __init__(self, registry: ToolRegistry) -> None:
        self._registry = registry

    def for_event_type(self, definition: EventTypeDefinition) -> tuple[ToolDefinition, ...]:
        return self._registry.list_allowed(definition.allowed_tools)
