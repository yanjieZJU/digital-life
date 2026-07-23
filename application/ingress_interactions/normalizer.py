"""Channel-entry normalization helpers."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .contracts import InteractionMessage, LLMMessage, MessageEvent


class InteractionNormalizer:
    """Convert ingress-facing InteractionMessage into an internal MessageEvent."""

    def normalize(
        self,
        message: InteractionMessage,
        *,
        source: str | None = None,
        role: str = "user",
        activated_skills: tuple[str, ...] = (),
    ) -> MessageEvent:
        event_metadata = dict(message.metadata)
        if message.correlation_id:
            event_metadata["correlation_id"] = message.correlation_id
        event_source = source or self._default_source(event_metadata)
        return MessageEvent(
            id=message.message_id,
            source=event_source,
            sender=message.actor_id,
            llm_message=LLMMessage(role=role, content=message.content),
            activated_skills=activated_skills,
            metadata=event_metadata,
        )

    @staticmethod
    def _default_source(metadata: Mapping[str, Any]) -> str:
        if metadata.get("external_channel") == "feedback":
            return "feedback"
        if metadata.get("external_channel") in {"scheduler", "webhook"}:
            return "environment"
        return "user"


__all__ = ["InteractionNormalizer"]
