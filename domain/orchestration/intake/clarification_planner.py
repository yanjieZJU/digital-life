"""Clarification planning for incomplete task contracts."""

from __future__ import annotations

from ..types import ClarificationRequest
from .models import Intent, SlotSet


class ClarificationPlanner:
    def __init__(self, questions: dict[str, str] | None = None) -> None:
        self._questions = dict(questions or {})

    def plan(self, intent: Intent, slots: SlotSet) -> ClarificationRequest:
        return self.generate(slots.missing_required)

    def generate(self, missing_slots: list[str]) -> ClarificationRequest:
        questions = [self._questions.get(slot, f"请补充 {slot}。") for slot in missing_slots]
        return ClarificationRequest(questions=questions[:3], missing_slots=missing_slots)


ClarificationGenerator = ClarificationPlanner


__all__ = ["ClarificationGenerator", "ClarificationPlanner"]
