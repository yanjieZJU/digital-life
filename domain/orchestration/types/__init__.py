"""Serializable orchestration MVP types."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal


TaskType = Literal["recurring_monitor", "one_shot", "reminder", "research"]
CapabilityStatus = Literal["available", "missing", "partial", "disabled"]
PlanType = Literal["runtime_task_list", "capability_development_task_list"]
PlanStatus = Literal["ready_for_execution", "blocked"]
OutcomeType = Literal[
    "clarification_request",
    "runtime_task_list",
    "capability_development_task_list",
    "speckit_request",
]


@dataclass(frozen=True)
class TaskAction:
    type: str
    channel: str | None = None
    params: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TaskContract:
    id: str
    type: TaskType
    domain: str
    goal: str
    action: TaskAction
    employee_id: str = ""
    source_message_event_id: str = ""
    target: dict[str, Any] = field(default_factory=dict)
    schedule: dict[str, Any] = field(default_factory=dict)
    condition: dict[str, Any] = field(default_factory=dict)
    constraints: dict[str, Any] = field(default_factory=dict)

    @property
    def task_type(self) -> TaskType:
        return self.type

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Capability:
    id: str
    name: str
    status: CapabilityStatus = "available"
    input_schema: dict[str, Any] = field(default_factory=dict)
    output_schema: dict[str, Any] = field(default_factory=dict)
    supports: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CapabilityCheckResult:
    ok: bool
    available: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    partial: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


CapabilityMatchResult = CapabilityCheckResult


@dataclass(frozen=True)
class TaskNode:
    id: str
    title: str
    type: str
    depends_on: list[str] = field(default_factory=list)
    required_capability: str | None = None
    input: dict[str, Any] = field(default_factory=dict)
    output: str | None = None

    @property
    def task_type(self) -> str:
        return self.type

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CapabilityGap:
    gap_id: str
    source_task_id: str
    missing_capability: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class OrchestrationPlan:
    plan_id: str
    source_task_id: str
    plan_type: PlanType
    status: PlanStatus
    tasks: list[TaskNode] = field(default_factory=list)
    capability_gap: CapabilityGap | None = None
    output_type: OutcomeType = "runtime_task_list"

    @property
    def id(self) -> str:
        return self.plan_id

    @property
    def source_contract_id(self) -> str:
        return self.source_task_id

    @property
    def list_type(self) -> str:
        if self.plan_type == "runtime_task_list":
            return "runtime"
        return "capability_development"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ClarificationRequest:
    questions: list[str]
    missing_slots: list[str] = field(default_factory=list)
    output_type: OutcomeType = "clarification_request"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SpecKitRequest:
    source_task_id: str
    capability_gap: CapabilityGap
    request: str
    expected_outputs: list[str] = field(
        default_factory=lambda: ["spec.md", "plan.md", "tasks.md", "tasks.json"]
    )
    output_type: OutcomeType = "speckit_request"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SpecKitPlanResult:
    spec_path: str
    plan_path: str
    tasks_path: str
    tasks_json_path: str
    task_list: OrchestrationPlan

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


OrchestrationOutcome = ClarificationRequest | OrchestrationPlan | SpecKitRequest


__all__ = [
    "Capability",
    "CapabilityCheckResult",
    "CapabilityGap",
    "CapabilityMatchResult",
    "ClarificationRequest",
    "OrchestrationOutcome",
    "OrchestrationPlan",
    "SpecKitPlanResult",
    "SpecKitRequest",
    "TaskAction",
    "TaskContract",
    "TaskNode",
]
