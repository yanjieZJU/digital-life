"""Project-owned runtime adapter contracts for Execution Semantics."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Mapping, Protocol

from .events import CanonicalExecutionEvent

from .contracts import ExecutionRequest


@dataclass(frozen=True)
class RuntimeExecutionResult:
    execution_id: str
    status: str
    output: Mapping[str, object] = field(default_factory=dict)
    error: str = ""


class RuntimeEnginePort(Protocol):
    def execute(self, request: ExecutionRequest) -> RuntimeExecutionResult: ...


class ExecutionEngineEventAdapter(Protocol):
    engine_name: str

    def to_canonical_events(self, engine_events: Iterable[Mapping[str, object]], *, run_id: str) -> tuple[CanonicalExecutionEvent, ...]: ...


__all__ = ["ExecutionEngineEventAdapter", "RuntimeEnginePort", "RuntimeExecutionResult"]
