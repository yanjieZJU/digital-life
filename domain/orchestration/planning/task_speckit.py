"""SpecKit package builder for complex task assignments."""

from __future__ import annotations

import json
from typing import Any

from ..intake.task_complexity import TaskComplexityDecision
from ..types import CapabilityGap, TaskAction, TaskContract
from .speckit_planner import SpecKitPlanner


class AssignedTaskSpeckitBuilder:
    """Build a serializable SpecKit package for a complex assigned task."""

    def __init__(
        self,
        *,
        speckit_planner: SpecKitPlanner | None = None,
    ) -> None:
        self._speckit_planner = speckit_planner or SpecKitPlanner()

    def build(
        self,
        *,
        task_id: str,
        title: str,
        description: str = "",
        priority: str = "medium",
        employee_id: str = "",
        decision: TaskComplexityDecision,
    ) -> dict[str, Any]:
        contract = TaskContract(
            id=f"assigned-{task_id}",
            employee_id=employee_id,
            source_message_event_id=task_id,
            type="one_shot",
            domain="assigned_task",
            goal=description.strip() or title.strip(),
            action=TaskAction(type="execute_complex_task", channel="task_workspace"),
            constraints={"priority": priority, "complexity_reason": decision.reason},
        )
        gap = CapabilityGap(
            gap_id=f"gap-{task_id}",
            source_task_id=contract.id,
            missing_capability="task.complex_execution_plan",
            reason=f"复杂任务需要先规格化拆解后执行：{decision.reason}",
        )
        planned = self._speckit_planner.plan(
            contract,
            gap,
            missing_capabilities=["task.specify", "task.plan", "task.breakdown"],
            base_path="speckit",
        )
        task_list = planned.task_list.to_dict()
        task_nodes = task_list.get("tasks") if isinstance(task_list.get("tasks"), list) else []
        files = {
            "spec.md": self._render_spec(title, description, priority, contract, gap),
            "plan.md": self._render_plan(title, task_nodes),
            "tasks.md": self._render_tasks(task_nodes),
            "tasks.json": json.dumps({"tasks": task_nodes}, ensure_ascii=False, indent=2),
        }
        return {
            "schema": "digital_employee.speckit.v1",
            "decision": decision.__dict__,
            "paths": {
                "spec_path": planned.spec_path,
                "plan_path": planned.plan_path,
                "tasks_path": planned.tasks_path,
                "tasks_json_path": planned.tasks_json_path,
            },
            "contract": contract.to_dict(),
            "capability_gap": gap.to_dict(),
            "task_list": task_list,
            "files": files,
            "workspace_note": "\n".join(
                [
                    "## SpecKit 拆解",
                    "- 先阅读 `speckit/spec.md` 明确目标和验收标准。",
                    "- 再按 `speckit/plan.md` 和 `speckit/tasks.md` 执行。",
                    "- 完成后写入 task_note，并通过 express_to_human 回复结果。",
                    "",
                ]
            ),
        }

    @staticmethod
    def _render_spec(title: str, description: str, priority: str, contract: TaskContract, gap: CapabilityGap) -> str:
        return "\n".join(
            [
                f"# SpecKit Specification: {title}",
                "",
                "## Goal",
                description.strip() or title.strip(),
                "",
                "## Source Task",
                f"- Contract ID: `{contract.id}`",
                f"- Priority: `{priority}`",
                "",
                "## Capability Gap",
                f"- Missing capability: `{gap.missing_capability}`",
                f"- Reason: {gap.reason}",
                "",
                "## Acceptance Criteria",
                "- 任务目标、边界和约束已被明确记录。",
                "- 实施计划已拆成可执行步骤。",
                "- 执行结果写入 task_note。",
                "- 最终结果通过 express_to_human 回复给用户。",
                "",
            ]
        )

    @staticmethod
    def _render_plan(title: str, task_nodes: list[dict[str, Any]]) -> str:
        lines = [
            f"# SpecKit Plan: {title}",
            "",
            "## Execution Strategy",
            "先完成规格化拆解，再按任务节点顺序执行，并保留执行证据。",
            "",
            "## Task Nodes",
        ]
        for node in task_nodes:
            lines.append(f"- `{node.get('id')}` {node.get('title')} ({node.get('required_capability')})")
        lines.append("")
        return "\n".join(lines)

    @staticmethod
    def _render_tasks(task_nodes: list[dict[str, Any]]) -> str:
        lines = ["# SpecKit Tasks", ""]
        for node in task_nodes:
            output = f" -> {node.get('output')}" if node.get("output") else ""
            lines.append(f"- [ ] `{node.get('id')}` {node.get('title')}{output}")
        lines.append("")
        return "\n".join(lines)


__all__ = ["AssignedTaskSpeckitBuilder"]
