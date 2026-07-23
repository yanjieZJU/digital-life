"""Flow events emitted by execution engines."""

from __future__ import annotations

from dataclasses import dataclass

from .core import FlowEvent


@dataclass(frozen=True, kw_only=True)
class ExecutionStartedEvent(FlowEvent):
    type: str = "ExecutionStartedEvent"
    layer: str = "execution"


@dataclass(frozen=True, kw_only=True)
class AgentStepStartedEvent(FlowEvent):
    type: str = "AgentStepStartedEvent"
    layer: str = "execution"


@dataclass(frozen=True, kw_only=True)
class AgentStepCompletedEvent(FlowEvent):
    type: str = "AgentStepCompletedEvent"
    layer: str = "execution"


@dataclass(frozen=True, kw_only=True)
class ActionProposedEvent(FlowEvent):
    type: str = "ActionProposedEvent"
    layer: str = "execution"


@dataclass(frozen=True, kw_only=True)
class ActionDispatchedEvent(FlowEvent):
    type: str = "ActionDispatchedEvent"
    layer: str = "execution"


@dataclass(frozen=True, kw_only=True)
class ObservationReceivedEvent(FlowEvent):
    type: str = "ObservationReceivedEvent"
    layer: str = "execution"


@dataclass(frozen=True, kw_only=True)
class ToolErrorEvent(FlowEvent):
    type: str = "ToolErrorEvent"
    layer: str = "execution"
    severity: str = "error"


@dataclass(frozen=True, kw_only=True)
class StateChangedEvent(FlowEvent):
    type: str = "StateChangedEvent"
    layer: str = "execution"


@dataclass(frozen=True, kw_only=True)
class ExecutionCompletedEvent(FlowEvent):
    type: str = "ExecutionCompletedEvent"
    layer: str = "execution"


@dataclass(frozen=True, kw_only=True)
class ExecutionFailedEvent(FlowEvent):
    type: str = "ExecutionFailedEvent"
    layer: str = "execution"
    severity: str = "error"


__all__ = [
    "ActionDispatchedEvent",
    "ActionProposedEvent",
    "AgentStepCompletedEvent",
    "AgentStepStartedEvent",
    "ExecutionCompletedEvent",
    "ExecutionFailedEvent",
    "ExecutionStartedEvent",
    "ObservationReceivedEvent",
    "StateChangedEvent",
    "ToolErrorEvent",
]
