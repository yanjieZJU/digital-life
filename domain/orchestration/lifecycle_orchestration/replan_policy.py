"""Replanning policy for lifecycle orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class ReplanDecision:
    should_replan: bool
    reason: str


class ReplanPolicy:
    """Decide whether execution feedback should trigger a new plan."""

    def evaluate(self, *, plan_state: str, feedback: Mapping[str, object] | None = None) -> ReplanDecision:
        feedback = feedback or {}
        if plan_state == "BLOCKED":
            return ReplanDecision(True, "blocked_plan")
        if bool(feedback.get("capability_gap")):
            return ReplanDecision(True, "capability_gap")
        if bool(feedback.get("requirements_changed")):
            return ReplanDecision(True, "requirements_changed")
        if str(feedback.get("execution_status", "")).lower() in {"failed", "stuck"}:
            return ReplanDecision(True, "execution_not_progressing")
        return ReplanDecision(False, "no_replan_signal")


__all__ = ["ReplanDecision", "ReplanPolicy"]
