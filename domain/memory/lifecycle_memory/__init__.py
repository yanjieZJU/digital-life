"""Lifecycle memory_layer migration manifest.

Owns context assembly, persona/prompt material, consciousness residue, recall,
and session/memory consolidation extracted from Hermes lifecycle modules.
"""

from __future__ import annotations

from domain.core.models import LifecycleLayer, LifecycleSourceSlice


LIFECYCLE_MEMORY_SLICES: tuple[LifecycleSourceSlice, ...] = (
    LifecycleSourceSlice(
        source_module="life_persona",
        layer=LifecycleLayer.MEMORY,
        target_package="domain.memory.context.selectors.persona",
        responsibility="Select and load digital employee persona context from app-space assets.",
        adapter_boundary="Hermes requests persona context through selectors; employee assets stay under apps/{employee_id}.",
    ),
    LifecycleSourceSlice(
        source_module="prompts",
        layer=LifecycleLayer.MEMORY,
        target_package="domain.identity.system_prompts",
        responsibility="Static L4 lifecycle system prompt definitions and overrides.",
        adapter_boundary="Hermes reads static system prompt text from domain memory.",
    ),
    LifecycleSourceSlice(
        source_module="heartbeat",
        layer=LifecycleLayer.MEMORY,
        target_package="domain.identity.wakeup_prompts",
        responsibility="Wake prompt rendering and context bundle text composition.",
        adapter_boundary="Hermes receives a rendered prompt bundle from domain memory.",
    ),
    LifecycleSourceSlice(
        source_module="consciousness",
        layer=LifecycleLayer.MEMORY,
        target_package="domain.memory.memory.consciousness",
        responsibility="Consciousness residue, sent-message log, diary-like continuity notes.",
        adapter_boundary="Hermes tools call memory_layer interfaces for reading and writing residue.",
    ),
    LifecycleSourceSlice(
        source_module="memory_consolidation",
        layer=LifecycleLayer.MEMORY,
        target_package="domain.memory.summaries",
        responsibility="Session digest, long/short summary generation, memory layer indexing.",
        adapter_boundary="Hermes session completion calls package consolidation service.",
    ),
    LifecycleSourceSlice(
        source_module="memory_recall",
        layer=LifecycleLayer.MEMORY,
        target_package="domain.memory.recall",
        responsibility="Keyword recall over persisted memory and session summaries.",
        adapter_boundary="Context assembler requests recall through package selector APIs.",
    ),
    LifecycleSourceSlice(
        source_module="vector_recall",
        layer=LifecycleLayer.MEMORY,
        target_package="domain.memory.recall.vector",
        responsibility="Embedding index, vector recall, and vector fallback behavior.",
        adapter_boundary="Context assembler requests vector recall through package selector APIs.",
    ),
    LifecycleSourceSlice(
        source_module="tasks",
        layer=LifecycleLayer.MEMORY,
        target_package="domain.memory.workspace_memory",
        responsibility="Workspace notes and task progress notes used as durable memory.",
        adapter_boundary="Workspace adapters expose notes through memory_layer selectors.",
    ),
)


__all__ = ["LIFECYCLE_MEMORY_SLICES"]
