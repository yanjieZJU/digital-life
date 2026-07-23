"""Rule-based intent classifier for the orchestration MVP."""

from __future__ import annotations

from .models import Intent, IntentRule


class IntentClassifier:
    def __init__(
        self,
        rules: tuple[IntentRule, ...] | list[IntentRule] = (),
        *,
        fallback: Intent | None = None,
    ) -> None:
        self._rules = tuple(rules)
        self._fallback = fallback or Intent(name="one_shot", domain="general", confidence=0.0)

    def classify(self, text: str, context: object | None = None) -> Intent:
        normalized = text or ""
        for rule in self._rules:
            if rule.matches(normalized):
                return Intent(name=rule.intent, domain=rule.domain, confidence=rule.confidence)
        return self._fallback


__all__ = ["IntentClassifier", "IntentRule"]
