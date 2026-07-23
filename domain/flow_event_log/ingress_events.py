"""Flow events emitted by ingress normalization and checks."""

from __future__ import annotations

from dataclasses import dataclass

from .core import FlowEvent


@dataclass(frozen=True, kw_only=True)
class MessageReceivedEvent(FlowEvent):
    type: str = "MessageReceivedEvent"
    layer: str = "ingress"


@dataclass(frozen=True, kw_only=True)
class MessageNormalizedEvent(FlowEvent):
    type: str = "MessageNormalizedEvent"
    layer: str = "ingress"


@dataclass(frozen=True, kw_only=True)
class IngressCheckPassedEvent(FlowEvent):
    type: str = "IngressCheckPassedEvent"
    layer: str = "ingress"


@dataclass(frozen=True, kw_only=True)
class IngressCheckRejectedEvent(FlowEvent):
    type: str = "IngressCheckRejectedEvent"
    layer: str = "ingress"
    severity: str = "warning"


__all__ = [
    "IngressCheckPassedEvent",
    "IngressCheckRejectedEvent",
    "MessageNormalizedEvent",
    "MessageReceivedEvent",
]
