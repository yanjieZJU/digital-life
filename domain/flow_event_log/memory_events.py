"""Flow events emitted by memory and context assembly."""

from __future__ import annotations

from dataclasses import dataclass

from .core import FlowEvent


@dataclass(frozen=True, kw_only=True)
class MemoryContextRequestedEvent(FlowEvent):
    type: str = "MemoryContextRequestedEvent"
    layer: str = "memory"


@dataclass(frozen=True, kw_only=True)
class PersonaLoadedEvent(FlowEvent):
    type: str = "PersonaLoadedEvent"
    layer: str = "memory"


@dataclass(frozen=True, kw_only=True)
class SkillContextLoadedEvent(FlowEvent):
    type: str = "SkillContextLoadedEvent"
    layer: str = "memory"


@dataclass(frozen=True, kw_only=True)
class MemoryRecallRequestedEvent(FlowEvent):
    type: str = "MemoryRecallRequestedEvent"
    layer: str = "memory"


@dataclass(frozen=True, kw_only=True)
class MemoryRecallCompletedEvent(FlowEvent):
    type: str = "MemoryRecallCompletedEvent"
    layer: str = "memory"


@dataclass(frozen=True, kw_only=True)
class MemoryWriteCommittedEvent(FlowEvent):
    type: str = "MemoryWriteCommittedEvent"
    layer: str = "memory"


@dataclass(frozen=True, kw_only=True)
class MemoryCondensationCompletedEvent(FlowEvent):
    type: str = "MemoryCondensationCompletedEvent"
    layer: str = "memory"


@dataclass(frozen=True, kw_only=True)
class ContextBudgetAppliedEvent(FlowEvent):
    type: str = "ContextBudgetAppliedEvent"
    layer: str = "memory"


__all__ = [
    "ContextBudgetAppliedEvent",
    "MemoryCondensationCompletedEvent",
    "MemoryContextRequestedEvent",
    "MemoryRecallCompletedEvent",
    "MemoryRecallRequestedEvent",
    "MemoryWriteCommittedEvent",
    "PersonaLoadedEvent",
    "SkillContextLoadedEvent",
]
