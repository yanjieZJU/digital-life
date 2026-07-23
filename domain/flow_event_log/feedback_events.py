"""Flow events emitted by feedback and lifecycle response layers."""

from __future__ import annotations

from dataclasses import dataclass

from .core import FlowEvent


@dataclass(frozen=True, kw_only=True)
class FeedbackSignalReceivedEvent(FlowEvent):
    type: str = "FeedbackSignalReceivedEvent"
    layer: str = "feedback"


@dataclass(frozen=True, kw_only=True)
class HumanReplyPlannedEvent(FlowEvent):
    type: str = "HumanReplyPlannedEvent"
    layer: str = "feedback"


@dataclass(frozen=True, kw_only=True)
class HumanReplySentEvent(FlowEvent):
    type: str = "HumanReplySentEvent"
    layer: str = "feedback"


@dataclass(frozen=True, kw_only=True)
class ProactiveReportEvaluatedEvent(FlowEvent):
    type: str = "ProactiveReportEvaluatedEvent"
    layer: str = "feedback"


@dataclass(frozen=True, kw_only=True)
class ProactiveReportSentEvent(FlowEvent):
    type: str = "ProactiveReportSentEvent"
    layer: str = "feedback"


@dataclass(frozen=True, kw_only=True)
class VitalsUpdatedEvent(FlowEvent):
    type: str = "VitalsUpdatedEvent"
    layer: str = "feedback"


@dataclass(frozen=True, kw_only=True)
class LifecycleEventScheduledEvent(FlowEvent):
    type: str = "LifecycleEventScheduledEvent"
    layer: str = "feedback"


@dataclass(frozen=True, kw_only=True)
class LifecycleEventConsumedEvent(FlowEvent):
    type: str = "LifecycleEventConsumedEvent"
    layer: str = "feedback"


@dataclass(frozen=True, kw_only=True)
class RunResultEvaluatedEvent(FlowEvent):
    type: str = "RunResultEvaluatedEvent"
    layer: str = "feedback"


__all__ = [
    "FeedbackSignalReceivedEvent",
    "HumanReplyPlannedEvent",
    "HumanReplySentEvent",
    "LifecycleEventConsumedEvent",
    "LifecycleEventScheduledEvent",
    "ProactiveReportEvaluatedEvent",
    "ProactiveReportSentEvent",
    "RunResultEvaluatedEvent",
    "VitalsUpdatedEvent",
]
