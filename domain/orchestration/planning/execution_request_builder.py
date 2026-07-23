"""Build execution_layer requests from orchestration task lists."""

from __future__ import annotations

from domain.execution.semantics import ExecutionRequest

from ..types import OrchestrationPlan, TaskContract, TaskNode


class ExecutionRequestBuilder:
    def from_task(
        self,
        *,
        employee_id: str,
        source_message_event_id: str,
        task_contract: TaskContract,
        task_list: OrchestrationPlan,
        task: TaskNode,
    ) -> ExecutionRequest:
        capability = task.required_capability or task.type
        return ExecutionRequest(
            execution_id=f"{source_message_event_id}:{task_list.plan_id}:{task.id}",
            task_node_id=task.id,
            runtime_capability=capability,
            execution_policy={
                "source": "orchestration",
                "employee_id": employee_id,
                "message_event_id": source_message_event_id,
                "task_contract_id": task_contract.id,
                "plan_id": task_list.plan_id,
                "plan_type": task_list.plan_type,
                "task_type": task.type,
                "depends_on": list(task.depends_on),
            },
            context_refs=tuple(ref for ref in (source_message_event_id, task_contract.id) if ref),
            result_contract=task.output or "default",
        )

    def from_task_list(
        self,
        *,
        employee_id: str,
        source_message_event_id: str,
        task_contract: TaskContract,
        task_list: OrchestrationPlan,
    ) -> tuple[ExecutionRequest, ...]:
        return tuple(
            self.from_task(
                employee_id=employee_id,
                source_message_event_id=source_message_event_id,
                task_contract=task_contract,
                task_list=task_list,
                task=task,
            )
            for task in task_list.tasks
        )


__all__ = ["ExecutionRequestBuilder"]
