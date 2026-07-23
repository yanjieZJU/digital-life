"""Runtime task-list planning."""

from __future__ import annotations

from domain.core.ids import new_id

from ..types import OrchestrationPlan, TaskContract, TaskNode


class RuntimeTaskPlanner:
    def build(self, contract: TaskContract, required_capabilities: list[str]) -> OrchestrationPlan:
        tasks = [
            TaskNode(
                id=f"T{index:03d}",
                title=f"Execute capability {capability}",
                type="capability_step",
                required_capability=capability,
                input=self._input_for(capability, contract),
                depends_on=[] if index == 1 else [f"T{index - 1:03d}"],
            )
            for index, capability in enumerate(required_capabilities, start=1)
        ]
        return OrchestrationPlan(
            plan_id=new_id("plan-runtime"),
            source_task_id=contract.id,
            plan_type="runtime_task_list",
            status="ready_for_execution",
            tasks=tasks,
            output_type="runtime_task_list",
        )

    @staticmethod
    def _input_for(capability: str, contract: TaskContract) -> dict[str, object]:
        return {
            "capability": capability,
            "contract": contract.to_dict(),
        }


__all__ = ["RuntimeTaskPlanner"]
