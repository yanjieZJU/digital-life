"""Plan state policy for lifecycle orchestration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Mapping


PlanState = Literal["DRAFT", "READY", "BLOCKED", "COMPLETED"]


@dataclass(frozen=True)
class PlanStateSnapshot:
    plan_id: str
    state: PlanState
    reason: str = ""
    metadata: Mapping[str, object] = field(default_factory=dict)


class PlanStatePolicy:
    """Derive a lifecycle-visible plan state from orchestration output."""

    def from_result_kind(self, *, plan_id: str | None, kind: str, plan_status: str | None = None) -> PlanStateSnapshot:
        if kind in {"execution_ready", "capability_development_ready"} and plan_status == "ready_for_execution":
            return PlanStateSnapshot(plan_id=plan_id or "", state="READY", reason=kind)
        if kind == "clarification_required":
            return PlanStateSnapshot(plan_id=plan_id or "", state="DRAFT", reason=kind)
        return PlanStateSnapshot(plan_id=plan_id or "", state="BLOCKED", reason=kind)


__all__ = ["PlanState", "PlanStatePolicy", "PlanStateSnapshot"]
