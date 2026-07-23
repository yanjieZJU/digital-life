"""Compatibility shim for persona context selection.

Employee-specific persona assets live under ``apps/{employee_id}``.  New code
should import from ``domain.memory.context.selectors.persona``; this
module remains for legacy callers.
"""

from __future__ import annotations

from domain.memory.context.selectors.persona import (
    LIFE_PERSONA,
    MISSING_LIFE_PERSONA,
    get_life_persona_path,
    load_life_persona,
)

DEFAULT_LIFE_PERSONA = MISSING_LIFE_PERSONA


__all__ = [
    "DEFAULT_LIFE_PERSONA",
    "LIFE_PERSONA",
    "MISSING_LIFE_PERSONA",
    "get_life_persona_path",
    "load_life_persona",
]
