"""ID helpers shared by L4 modules."""

from __future__ import annotations

from uuid import uuid4


def new_id(prefix: str) -> str:
    """Create a short, stable-looking ID with a module prefix."""
    safe_prefix = prefix.strip().replace("_", "-").lower()
    return f"{safe_prefix}_{uuid4().hex[:12]}"

