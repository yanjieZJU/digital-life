"""Hermes-specific console adapter surface.

Application workflows import this module through ``backend.application`` provider
resolution, not directly. This keeps Hermes details out of the application
package while preserving the existing console behavior.
"""

from __future__ import annotations

from typing import Any


def list_event_prompt_configs(overrides: dict[str, str]) -> list[dict[str, Any]]:
    """Return event prompt configs for each registered event type.

    Prompt content is read from the event registry (YAML-merged definition),
    not from heartbeat module variables. Overrides are still supported.
    """
    from domain.lifecycle.event_registry import list_event_types

    items: list[dict[str, Any]] = []
    for definition in list_event_types():
        prompt_content = definition.prompt_template or ""
        items.append({
            "type_id": definition.type_id,
            "display_name": definition.display_name,
            "trigger_type": definition.trigger_type.value,
            "trigger_description": definition.trigger_description,
            "description": definition.description,
            "payload_schema": dict(definition.payload_schema or {}),
            "allowed_tools": list(definition.allowed_tools or ()),
            "context_policy": dict(definition.context_policy or {}),
            "auth_policy": dict(definition.auth_policy or {}),
            "prompt_key": definition.type_id,
            "prompt_content": overrides.get(definition.type_id, prompt_content),
            "prompt_original": prompt_content,
            "prompt_overridden": bool(definition.type_id in overrides),
            "prompt_file": "config/event_types.yaml",
        })
    return items


def hot_reload_prompt(name: str, content: str) -> None:
    """Hot-reload a prompt template into the running instance.

    Event-type prompts update the registry entry.
    Special names: LIFE_PERSONA is handled separately.
    """
    if name == "LIFE_PERSONA":
        import domain.memory.context.selectors.persona as persona_selector
        persona_selector.LIFE_PERSONA = content
        return
        return

    # Update the registry entry for event-type prompts
    from domain.lifecycle.event_registry import get_event_type, _registry

    definition = get_event_type(name)
    if definition:
        from dataclasses import replace
        updated = replace(definition, prompt_template=content)
        _registry._definitions[name] = updated


def recent_nurture_log(*, hours: int = 24) -> list[dict[str, Any]]:
    from domain.vital import recent_nurture_log as _recent_nurture_log

    return _recent_nurture_log(hours=hours)


def apply_nurture(*, kind: str, deltas: dict[str, float], raw_text: str = "", source: str = "") -> Any:
    from domain.vital import apply_nurture as _apply_nurture

    return _apply_nurture(kind=kind, deltas=deltas, raw_text=raw_text, source=source)


def predict_threshold_crossings() -> list[dict[str, Any]]:
    return []


__all__ = [
    "apply_nurture",
    "hot_reload_prompt",
    "list_event_prompt_configs",
    "predict_threshold_crossings",
    "recent_nurture_log",
]
