"""Digital-life feedback ingress normalization."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from uuid import uuid4

from ..contracts import InteractionMessage


class FeedbackIngress:
    """Convert digital-life feedback messages into InteractionMessage."""

    def normalize(
        self,
        feedback: Mapping[str, Any] | Any,
        *,
        digital_life_id: str = "",
        feedback_source: str = "feedback_layer",
        message_id: str | None = None,
        correlation_id: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> InteractionMessage:
        payload = dict(feedback) if isinstance(feedback, Mapping) else vars(feedback)
        content = str(payload.get("content") or payload.get("text") or payload.get("message") or "")
        life_id = str(payload.get("digital_life_id") or digital_life_id or "")
        source = str(payload.get("feedback_source") or feedback_source)
        input_id = str(payload.get("message_id") or payload.get("id") or message_id or f"feedback:{uuid4().hex}")
        actor_id = str(payload.get("actor_id") or payload.get("sender") or life_id or source)
        combined_metadata = {
            "external_channel": "feedback",
            "digital_life_id": life_id,
            "feedback_source": source,
        }
        combined_metadata.update(dict(metadata or {}))
        combined_metadata.update(dict(payload.get("metadata") or {}))

        return InteractionMessage(
            message_id=input_id,
            actor_id=actor_id,
            content=content,
            metadata=combined_metadata,
            correlation_id=correlation_id or str(payload.get("correlation_id") or "") or None,
        )


__all__ = ["FeedbackIngress"]
