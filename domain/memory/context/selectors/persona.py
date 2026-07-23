"""Persona context selector.

Employee-specific persona text is an app asset, stored under
``apps/{employee_id}/persona/LIFE_PERSONA.md``.  The memory context layer only
selects and loads that material for prompt assembly.
"""

from __future__ import annotations

from pathlib import Path

MISSING_LIFE_PERSONA = (
    "Persona is loaded from apps/{employee_id}/persona/LIFE_PERSONA.md. "
    "Create that file in the digital employee app space."
)


def get_life_persona_path(instance_id: str | None = None) -> Path:
    """Return the app-space persona prompt path for an employee instance."""
    from infrastructure.config import get_app_persona_path

    return get_app_persona_path(instance_id)


def load_life_persona(instance_id: str | None = None) -> str:
    """Load the active employee persona from the app-space instance directory."""
    try:
        content = get_life_persona_path(instance_id).read_text(encoding="utf-8").strip()
        if content:
            return content
    except Exception:
        return MISSING_LIFE_PERSONA
    return MISSING_LIFE_PERSONA


LIFE_PERSONA = load_life_persona()


__all__ = [
    "LIFE_PERSONA",
    "MISSING_LIFE_PERSONA",
    "get_life_persona_path",
    "load_life_persona",
]
