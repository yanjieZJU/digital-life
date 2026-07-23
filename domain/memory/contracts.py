"""Memory / Context contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping


@dataclass(frozen=True)
class PromptBundle:
    bundle_id: str
    actor_context: Mapping[str, object] = field(default_factory=dict)
    persona_context: str = ""
    event_context: Mapping[str, object] = field(default_factory=dict)
    memory_refs: tuple[str, ...] = ()
    skill_refs: tuple[str, ...] = ()
    workspace_refs: tuple[str, ...] = ()
    rendered_prompt_sections: tuple[str, ...] = ()
    token_budget: int | None = None
    source_attribution: Mapping[str, str] = field(default_factory=dict)


def assemble_prompt_bundle(
    *,
    bundle_id: str,
    persona_context: str = "",
    rendered_prompt_sections: tuple[str, ...] = (),
    token_budget: int | None = None,
) -> PromptBundle:
    """Create a minimal auditable Prompt Bundle without invoking a model."""

    return PromptBundle(
        bundle_id=bundle_id,
        persona_context=persona_context,
        rendered_prompt_sections=rendered_prompt_sections,
        token_budget=token_budget,
    )


__all__ = ["PromptBundle", "assemble_prompt_bundle"]

