"""Event security policy boundary."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from domain.core.models import EventTypeDefinition


SENSITIVE_KEYS = {"api_key", "authorization", "password", "secret", "token"}


@dataclass(frozen=True)
class EventSecurityDecision:
    allowed: bool
    payload: Mapping[str, Any]
    reason: str = ""


class EventSecurityPolicy:
    """Authorize and sanitize event payloads before they enter the queue."""

    def authorize(
        self,
        definition: EventTypeDefinition,
        payload: Mapping[str, Any] | None,
        *,
        actor_id: str | None = None,
    ) -> EventSecurityDecision:
        policy = dict(definition.auth_policy)
        if self._requires_actor(policy) and not actor_id:
            return EventSecurityDecision(False, {}, "actor_required")

        allowed_actors = tuple(str(actor) for actor in policy.get("allowed_actors", ()) or ())
        if allowed_actors and str(actor_id) not in allowed_actors:
            return EventSecurityDecision(False, {}, "actor_not_allowed")

        return EventSecurityDecision(True, sanitize_payload(payload or {}), "allowed")

    @staticmethod
    def _requires_actor(policy: Mapping[str, Any]) -> bool:
        return bool(
            policy.get("required_actor")
            or policy.get("require_actor")
            or policy.get("actor_required")
        )


def sanitize_payload(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    """Return a copy with credential-looking values redacted."""

    sanitized: dict[str, Any] = {}
    for key, value in payload.items():
        key_text = str(key)
        if any(secret in key_text.lower() for secret in SENSITIVE_KEYS):
            sanitized[key_text] = "[redacted]"
        elif isinstance(value, Mapping):
            sanitized[key_text] = sanitize_payload(value)
        elif isinstance(value, list):
            sanitized[key_text] = [sanitize_payload(item) if isinstance(item, Mapping) else item for item in value]
        else:
            sanitized[key_text] = value
    return sanitized


__all__ = ["EventSecurityDecision", "EventSecurityPolicy", "SENSITIVE_KEYS", "sanitize_payload"]
