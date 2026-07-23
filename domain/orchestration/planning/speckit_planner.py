"""SpecKit-oriented planning for complex capability development."""

from __future__ import annotations

from domain.core.ids import new_id

from ..types import CapabilityGap, OrchestrationPlan, SpecKitPlanResult, SpecKitRequest, TaskContract, TaskNode


class SpecKitPlanner:
    def should_use(self, missing_capabilities: list[str]) -> bool:
        return len(missing_capabilities) > 1

    def plan(
        self,
        contract: TaskContract,
        gap: CapabilityGap,
        *,
        missing_capabilities: list[str] | tuple[str, ...] = (),
        base_path: str | None = None,
    ) -> SpecKitPlanResult:
        capability_id = self._capability_path_id(gap.missing_capability)
        root = (base_path or f"specs/capabilities/{capability_id}").rstrip("/")
        request = self.build_request(contract, gap)
        capabilities = list(missing_capabilities) or [gap.missing_capability]
        task_list = OrchestrationPlan(
            plan_id=new_id("plan-speckit"),
            source_task_id=contract.id,
            plan_type="capability_development_task_list",
            status="ready_for_execution",
            tasks=[
                TaskNode(
                    id="S001",
                    title="Draft capability specification",
                    type="speckit_specification",
                    required_capability="speckit.specify",
                    input={
                        "request": request.to_dict(),
                        "missing_capabilities": capabilities,
                        "artifact_path": f"{root}/spec.md",
                    },
                    depends_on=[],
                    output="spec.md",
                ),
                TaskNode(
                    id="S002",
                    title="Create implementation plan",
                    type="speckit_plan",
                    required_capability="speckit.plan",
                    input={
                        "source_spec": f"{root}/spec.md",
                        "artifact_path": f"{root}/plan.md",
                    },
                    depends_on=["S001"],
                    output="plan.md",
                ),
                TaskNode(
                    id="S003",
                    title="Generate implementation tasks",
                    type="speckit_tasks",
                    required_capability="speckit.tasks",
                    input={
                        "source_plan": f"{root}/plan.md",
                        "tasks_path": f"{root}/tasks.md",
                        "tasks_json_path": f"{root}/tasks.json",
                    },
                    depends_on=["S002"],
                    output="tasks.json",
                ),
            ],
            capability_gap=gap,
            output_type="capability_development_task_list",
        )
        return SpecKitPlanResult(
            spec_path=f"{root}/spec.md",
            plan_path=f"{root}/plan.md",
            tasks_path=f"{root}/tasks.md",
            tasks_json_path=f"{root}/tasks.json",
            task_list=task_list,
        )

    def build_request(self, contract: TaskContract, gap: CapabilityGap) -> SpecKitRequest:
        return SpecKitRequest(
            source_task_id=contract.id,
            capability_gap=gap,
            request=(
                f"Create a capability-development specification for {gap.missing_capability}. "
                "Produce spec.md, plan.md, tasks.md, and tasks.json."
            ),
        )

    @staticmethod
    def _capability_path_id(capability_id: str) -> str:
        return "".join(char if char.isalnum() or char in {"-", "_"} else "_" for char in capability_id).strip("_")

__all__ = ["SpecKitPlanner"]
