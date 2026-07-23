"""Service contracts for the orchestration layer."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Literal, Mapping

from domain.execution.semantics import ExecutionRequest

from ..types import ClarificationRequest, OrchestrationPlan, TaskContract


OrchestrationResultKind = Literal[
    "clarification_required",
    "execution_ready",
    "capability_development_ready",
    "blocked",
]


@dataclass(frozen=True)
class OrchestrationRequest:
    employee_id: str
    message_event_id: str
    source: str
    text: str
    sender_id: str | None
    occurred_at: datetime
    memory_context: Mapping[str, Any] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["occurred_at"] = self.occurred_at.isoformat()
        return data


@dataclass(frozen=True)
class OrchestrationResult:
    kind: OrchestrationResultKind
    plan_id: str | None = None
    task_contract: TaskContract | None = None
    clarification: ClarificationRequest | None = None
    execution_request: ExecutionRequest | None = None
    blocked_reason: str | None = None
    debug: Mapping[str, Any] = field(default_factory=dict)
    plan: OrchestrationPlan | None = None
    execution_requests: tuple[ExecutionRequest, ...] = ()

    @classmethod
    def clarification_required(
        cls,
        *,
        clarification: ClarificationRequest,
        debug: Mapping[str, Any] | None = None,
    ) -> "OrchestrationResult":
        return cls(kind="clarification_required", clarification=clarification, debug=debug or {})

    @classmethod
    def execution_ready(
        cls,
        *,
        plan: OrchestrationPlan,
        task_contract: TaskContract,
        execution_requests: tuple[ExecutionRequest, ...],
        debug: Mapping[str, Any] | None = None,
    ) -> "OrchestrationResult":
        return cls(
            kind="execution_ready",
            plan_id=plan.plan_id,
            task_contract=task_contract,
            execution_request=execution_requests[0] if execution_requests else None,
            execution_requests=execution_requests,
            debug=debug or {},
            plan=plan,
        )

    @classmethod
    def capability_development_ready(
        cls,
        *,
        plan: OrchestrationPlan,
        task_contract: TaskContract,
        execution_requests: tuple[ExecutionRequest, ...],
        debug: Mapping[str, Any] | None = None,
    ) -> "OrchestrationResult":
        return cls(
            kind="capability_development_ready",
            plan_id=plan.plan_id,
            task_contract=task_contract,
            execution_request=execution_requests[0] if execution_requests else None,
            execution_requests=execution_requests,
            debug=debug or {},
            plan=plan,
        )

    @classmethod
    def blocked(
        cls,
        *,
        reason: str,
        debug: Mapping[str, Any] | None = None,
    ) -> "OrchestrationResult":
        return cls(kind="blocked", blocked_reason=reason, debug=debug or {})

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "plan_id": self.plan_id,
            "task_contract": self.task_contract.to_dict() if self.task_contract else None,
            "clarification": self.clarification.to_dict() if self.clarification else None,
            "execution_request": _execution_request_to_dict(self.execution_request),
            "execution_requests": [_execution_request_to_dict(request) for request in self.execution_requests],
            "blocked_reason": self.blocked_reason,
            "debug": dict(self.debug),
            "plan": self.plan.to_dict() if self.plan else None,
        }


def _execution_request_to_dict(request: ExecutionRequest | None) -> dict[str, Any] | None:
    if request is None:
        return None
    return {
        "execution_id": request.execution_id,
        "task_node_id": request.task_node_id,
        "runtime_capability": request.runtime_capability,
        "execution_policy": dict(request.execution_policy),
        "context_refs": list(request.context_refs),
        "interrupt_policy": request.interrupt_policy,
        "result_contract": request.result_contract,
    }


__all__ = ["OrchestrationRequest", "OrchestrationResult", "OrchestrationResultKind"]
