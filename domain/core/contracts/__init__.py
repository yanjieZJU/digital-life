"""Cross-module protocol contracts.

Concrete modules should depend on these protocols instead of importing each
other's storage or runtime internals.
"""

from __future__ import annotations

from typing import Protocol

from domain.core.models import AgentRun, AgentRunResult, EventInstance, EventTypeDefinition, PromptBundle, ToolDefinition


class EventRegistry(Protocol):
    def register(self, definition: EventTypeDefinition) -> None: ...

    def get(self, type_id: str) -> EventTypeDefinition | None: ...


class EventQueue(Protocol):
    def enqueue(self, event: EventInstance) -> EventInstance: ...

    def next_pending(self, agent_id: str | None = None) -> EventInstance | None: ...

    def mark_done(self, event_id: str) -> None: ...


class ContextAssembler(Protocol):
    def assemble(self, event: EventInstance) -> PromptBundle: ...


class ToolRegistry(Protocol):
    def register(self, tool: ToolDefinition) -> None: ...

    def list_allowed(self, names: tuple[str, ...]) -> tuple[ToolDefinition, ...]: ...


class ToolInvoker(Protocol):
    def invoke(self, name: str, args: dict) -> str: ...


class AgentRuntime(Protocol):
    def run(self, run: AgentRun) -> AgentRunResult: ...
