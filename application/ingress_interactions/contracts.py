"""Internal event contracts produced by ingress interactions adapters."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence
from uuid import uuid4


def _event_id() -> str:
    return f"evt_{uuid4().hex}"


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class LLMMessage:
    role: str
    content: str


@dataclass(frozen=True)
class InteractionMessage:
    """External-channel-neutral message shape produced by ingress adapters."""

    message_id: str
    actor_id: str
    content: str
    metadata: Mapping[str, Any] = field(default_factory=dict)
    received_at: str = field(default_factory=_timestamp)
    correlation_id: str | None = None


@dataclass(frozen=True, kw_only=True)
class BaseEvent:
    id: str = field(default_factory=_event_id)
    source: str
    timestamp: str = field(default_factory=_timestamp)
    metadata: Mapping[str, Any] = field(default_factory=dict)
    type: str = field(default="BaseEvent", init=False)


@dataclass(frozen=True, kw_only=True)
class MessageEvent(BaseEvent):
    """User, environment, or agent message after external ingress normalization."""

    sender: str
    llm_message: LLMMessage
    activated_skills: Sequence[str] = field(default_factory=tuple)
    type: str = field(default="MessageEvent", init=False)

    @property
    def message_id(self) -> str:
        return self.id

    @property
    def actor_id(self) -> str:
        return self.sender

    @property
    def content(self) -> str:
        return self.llm_message.content

    @property
    def correlation_id(self) -> str | None:
        value = self.metadata.get("correlation_id")
        return str(value) if value else None


InteractionInput = InteractionMessage


__all__ = [
    "BaseEvent",
    "InteractionInput",
    "InteractionMessage",
    "LLMMessage",
    "MessageEvent",
]
