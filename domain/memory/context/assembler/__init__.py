"""Prompt bundle assembly."""

from __future__ import annotations

import json

from domain.core.contracts import EventRegistry
from domain.core.models import EventInstance, PromptBundle
from domain.execution.recovery import ExecutionRecoveryService


class StaticContextAssembler:
    """Minimal assembler used while extracting real memory/workspace selectors."""

    def assemble(self, event: EventInstance) -> PromptBundle:
        return PromptBundle(
            system="You are an L4 digital life runtime.",
            event_context=f"Event type: {event.type_id}\nPayload: {dict(event.payload)}",
        )


class EventPackageContextAssembler:
    """Assemble context from an event type definition.

    This is the new default direction: event packages own their wakeup prompt,
    allowed tools, and context policy; selectors for memory/workspaces/vitals can
    be attached behind this assembler without changing callers.
    """

    def __init__(
        self,
        registry: EventRegistry,
        system_prompt: str | None = None,
        execution_recovery: ExecutionRecoveryService | None = None,
    ) -> None:
        self._registry = registry
        self._system_prompt = system_prompt or "You are an L4 digital life runtime."
        self._execution_recovery = execution_recovery

    def assemble(self, event: EventInstance) -> PromptBundle:
        definition = self._registry.get(event.type_id)
        if definition is None:
            return StaticContextAssembler().assemble(event)

        event_context = "\n\n".join(
            part
            for part in (
                definition.prompt_template.strip(),
                self._event_details(event),
                self._policy_details(definition.context_policy),
            )
            if part
        )
        return PromptBundle(
            system=self._system_prompt,
            event_context=event_context,
            execution_context=self._execution_context(event),
        )

    @staticmethod
    def _event_details(event: EventInstance) -> str:
        details = {
            "event_id": event.id,
            "type_id": event.type_id,
            "trigger_type": event.trigger_type.value,
            "agent_id": event.agent_id,
            "workspace_id": event.workspace_id,
            "fire_at": event.fire_at,
            "payload": dict(event.payload),
        }
        if event.context_hint:
            details["context_hint"] = event.context_hint
        return "## Event Details\n\n```json\n" + json.dumps(details, ensure_ascii=False, indent=2) + "\n```"

    @staticmethod
    def _policy_details(policy: object) -> str:
        if not policy:
            return ""
        return "## Context Policy\n\n```json\n" + json.dumps(policy, ensure_ascii=False, indent=2) + "\n```"

    def _execution_context(self, event: EventInstance) -> str:
        if self._execution_recovery is None:
            return ""
        return self._execution_recovery.render_open_items(agent_id=event.agent_id)
