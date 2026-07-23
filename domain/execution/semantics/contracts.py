"""Execution Semantics contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping


@dataclass(frozen=True)
class ExecutionRequest:
    execution_id: str
    task_node_id: str
    runtime_capability: str
    execution_policy: Mapping[str, object] = field(default_factory=dict)
    context_refs: tuple[str, ...] = ()
    interrupt_policy: str = "default"
    result_contract: str = "default"


@dataclass(frozen=True)
class ExecutionState:
    execution_id: str
    status: str
    progress: float = 0.0
    current_node_id: str | None = None
    recovery_refs: tuple[str, ...] = ()
    last_result: Mapping[str, object] = field(default_factory=dict)


__all__ = ["ExecutionRequest", "ExecutionState"]

