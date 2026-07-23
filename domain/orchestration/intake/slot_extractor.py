"""Slot extraction for orchestration task intake."""

from __future__ import annotations

from .models import Intent, SlotRule, SlotSet


class SlotExtractor:
    def __init__(
        self,
        slot_rules: tuple[SlotRule, ...] | list[SlotRule] = (),
        *,
        required_slots: dict[tuple[str, str], tuple[str, ...]] | None = None,
    ) -> None:
        self._slot_rules = tuple(slot_rules)
        self._required_slots = dict(required_slots or {})

    def extract(self, text: str, intent: Intent, context: object | None = None) -> SlotSet:
        text = text or ""
        slots: dict[str, object] = {
            "goal": text.strip(),
            "task_type": intent.name,
            "domain": intent.domain,
        }

        for rule in self._slot_rules:
            value = rule.extract(text)
            if value not in (None, ""):
                slots[rule.name] = value

        return SlotSet(values=slots, missing_required=self._missing_slots(slots))

    def _missing_slots(self, slots: dict[str, object]) -> list[str]:
        task_type = str(slots.get("task_type", ""))
        domain = str(slots.get("domain", ""))
        required = self._required_slots.get((task_type, domain)) or self._required_slots.get((task_type, "*")) or ()
        return [slot for slot in required if slot not in slots]


__all__ = ["SlotExtractor", "SlotRule"]
