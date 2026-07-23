"""Flow events emitted by orchestration planning."""

from __future__ import annotations

from dataclasses import dataclass

from .core import FlowEvent


@dataclass(frozen=True, kw_only=True)
class OrchestrationStartedEvent(FlowEvent):
    type: str = "OrchestrationStartedEvent"
    layer: str = "orchestration"


@dataclass(frozen=True, kw_only=True)
class IntentClassifiedEvent(FlowEvent):
    type: str = "IntentClassifiedEvent"
    layer: str = "orchestration"


@dataclass(frozen=True, kw_only=True)
class SlotExtractedEvent(FlowEvent):
    type: str = "SlotExtractedEvent"
    layer: str = "orchestration"


@dataclass(frozen=True, kw_only=True)
class ClarificationRequiredEvent(FlowEvent):
    type: str = "ClarificationRequiredEvent"
    layer: str = "orchestration"
    severity: str = "warning"


@dataclass(frozen=True, kw_only=True)
class CapabilityMatchedEvent(FlowEvent):
    type: str = "CapabilityMatchedEvent"
    layer: str = "orchestration"


@dataclass(frozen=True, kw_only=True)
class CapabilityMissingEvent(FlowEvent):
    type: str = "CapabilityMissingEvent"
    layer: str = "orchestration"
    severity: str = "warning"


@dataclass(frozen=True, kw_only=True)
class PlanCreatedEvent(FlowEvent):
    type: str = "PlanCreatedEvent"
    layer: str = "orchestration"


@dataclass(frozen=True, kw_only=True)
class ExecutionRequestCreatedEvent(FlowEvent):
    type: str = "ExecutionRequestCreatedEvent"
    layer: str = "orchestration"


@dataclass(frozen=True, kw_only=True)
class OrchestrationCompletedEvent(FlowEvent):
    type: str = "OrchestrationCompletedEvent"
    layer: str = "orchestration"


__all__ = [
    "CapabilityMatchedEvent",
    "CapabilityMissingEvent",
    "ClarificationRequiredEvent",
    "ExecutionRequestCreatedEvent",
    "IntentClassifiedEvent",
    "OrchestrationCompletedEvent",
    "OrchestrationStartedEvent",
    "PlanCreatedEvent",
    "SlotExtractedEvent",
]
