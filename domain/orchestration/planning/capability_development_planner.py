"""Capability-development task-list planning."""

from __future__ import annotations

from domain.core.ids import new_id

from ..types import CapabilityGap, OrchestrationPlan, TaskContract, TaskNode


class CapabilityDevelopmentPlanner:
    def build(self, contract: TaskContract, gap: CapabilityGap) -> OrchestrationPlan:
        capability = gap.missing_capability
        tasks = [
            TaskNode(id="D001", title=f"Define capability contract for {capability}", type="development"),
            TaskNode(
                id="D002",
                title=f"Implement provider boundary for {capability}",
                type="development",
                depends_on=["D001"],
            ),
            TaskNode(
                id="D003",
                title=f"Define error and result handling for {capability}",
                type="development",
                depends_on=["D002"],
            ),
            TaskNode(
                id="D004",
                title=f"Add acceptance coverage for {capability}",
                type="test_planning",
                depends_on=["D002"],
            ),
        ]
        return OrchestrationPlan(
            plan_id=new_id("plan-dev"),
            source_task_id=contract.id,
            plan_type="capability_development_task_list",
            status="ready_for_execution",
            tasks=tasks,
            capability_gap=gap,
            output_type="capability_development_task_list",
        )


__all__ = ["CapabilityDevelopmentPlanner"]
