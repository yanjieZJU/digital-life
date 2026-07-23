"""Deterministic pre-model ingress checks."""

from __future__ import annotations

from uuid import uuid4

from application.ingress_interactions import MessageEvent

from .contracts import CheckDecision


class IngressChecker:
    """Block input that does not require model/domain reasoning to reject."""

    def __init__(self, blocked_terms: set[str] | None = None) -> None:
        self._blocked_terms = {term.lower() for term in (blocked_terms or set())}
        self._seen_input_ids: set[str] = set()

    def evaluate(self, event: MessageEvent) -> CheckDecision:
        reasons: list[str] = []
        payload = dict(event.metadata)
        text = event.content.strip()

        if event.id in self._seen_input_ids:
            return self._decision(event, "duplicate", ("duplicate_input",), payload)
        self._seen_input_ids.add(event.id)

        if not event.sender:
            reasons.append("missing_actor_id")
        if not text and not payload:
            reasons.append("empty_message")
        elif not text:
            reasons.append("missing_text")
        lowered = text.lower()
        if any(term in lowered for term in self._blocked_terms):
            reasons.append("blocked_term")

        if "blocked_term" in reasons:
            return self._decision(event, "blocked", tuple(reasons), payload)
        if reasons:
            return self._decision(event, "invalid", tuple(reasons), payload)
        return self._decision(event, "accepted", (), payload)

    def _decision(
        self,
        event: MessageEvent,
        status: str,
        reasons: tuple[str, ...],
        payload: dict[str, object],
    ) -> CheckDecision:
        return CheckDecision(
            decision_id=f"gd_{uuid4().hex}",
            input_id=event.id,
            status=status,
            reasons=reasons,
            sanitized_payload={"text": event.content, **payload},
        )


__all__ = ["IngressChecker"]
