"""Capability gap planning."""

from __future__ import annotations

from domain.core.ids import new_id

from ..types import CapabilityCheckResult, CapabilityGap, TaskContract


class CapabilityGapPlanner:
    def plan(
        self,
        *,
        contract: TaskContract,
        required_capabilities: list[str],
        match: CapabilityCheckResult,
    ) -> CapabilityGap:
        missing_capability = match.missing[0] if match.missing else required_capabilities[0]
        return self.build(contract, missing_capability)

    def build(self, contract: TaskContract, missing_capability: str) -> CapabilityGap:
        return CapabilityGap(
            gap_id=new_id("gap"),
            source_task_id=contract.id,
            missing_capability=missing_capability,
            reason=f"系统缺少 {missing_capability} 能力，无法完成任务：{contract.goal}",
        )


__all__ = ["CapabilityGapPlanner"]
