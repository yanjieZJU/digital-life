"""Session-level context engineering capability."""

from .assembler import EventPackageContextAssembler, StaticContextAssembler
from .selectors import (
    LIFE_PERSONA,
    MISSING_LIFE_PERSONA,
    get_life_persona_path,
    load_life_persona,
)
from domain.identity.system_prompts import L4_LIFECYCLE_PROMPT
from domain.identity.wakeup_prompts import format_pending_events

DEFAULT_LIFE_PERSONA = MISSING_LIFE_PERSONA

__all__ = [
    "EventPackageContextAssembler",
    "DEFAULT_LIFE_PERSONA",
    "L4_LIFECYCLE_PROMPT",
    "LIFE_PERSONA",
    "MISSING_LIFE_PERSONA",
    "StaticContextAssembler",
    "format_pending_events",
    "get_life_persona_path",
    "load_life_persona",
]
