"""Context material selectors.

Selectors locate and load context material without owning employee-specific
assets.  Concrete employee files live under ``apps/{employee_id}``.
"""

from .persona import (
    LIFE_PERSONA,
    MISSING_LIFE_PERSONA,
    get_life_persona_path,
    load_life_persona,
)

__all__ = [
    "LIFE_PERSONA",
    "MISSING_LIFE_PERSONA",
    "get_life_persona_path",
    "load_life_persona",
]
