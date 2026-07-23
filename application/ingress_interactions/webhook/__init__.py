"""Webhook ingress interactions normalization."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from uuid import uuid4

from ..contracts import InteractionMessage


class WebhookIngress:
    """Convert external webhook payloads into InteractionMessage."""

    def normalize(
        self,
        *,
        headers: Mapping[str, str] | None = None,
        body: Mapping[str, Any] | None = None,
        actor_id: str = "webhook",
        message_id: str | None = None,
    ) -> InteractionMessage:
        normalized_headers = dict(headers or {})
        payload = dict(body or {})
        text = payload.get("text") or payload.get("message") or ""
        payload.pop("text", None)
        payload.pop("message", None)
        payload["external_channel"] = "webhook"
        return InteractionMessage(
            message_id=message_id or f"in_{uuid4().hex}",
            actor_id=actor_id,
            content=str(text),
            metadata=payload,
            correlation_id=normalized_headers.get("X-Request-ID") or normalized_headers.get("x-request-id"),
        )


__all__ = ["WebhookIngress"]
