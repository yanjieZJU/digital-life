"""Routing helpers for orchestration results."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from ..service import OrchestrationResult


RouteAction = Literal["reply", "execute", "block"]


@dataclass(frozen=True)
class OrchestrationRoute:
    action: RouteAction
    reason: str
    plan_id: str | None = None
    execution_ids: tuple[str, ...] = field(default_factory=tuple)


class OrchestrationRouter:
    """Convert a planning result into the next application-level action."""

    def route(self, result: OrchestrationResult) -> OrchestrationRoute:
        if result.kind == "clarification_required":
            return OrchestrationRoute(action="reply", reason="clarification_required", plan_id=result.plan_id)
        if result.kind == "blocked":
            return OrchestrationRoute(action="block", reason=result.blocked_reason or "blocked", plan_id=result.plan_id)
        if result.kind in {"execution_ready", "capability_development_ready"}:
            return OrchestrationRoute(
                action="execute",
                reason=result.kind,
                plan_id=result.plan_id,
                execution_ids=tuple(request.execution_id for request in result.execution_requests),
            )
        return OrchestrationRoute(action="block", reason=f"unsupported_result_kind:{result.kind}", plan_id=result.plan_id)


__all__ = ["OrchestrationRoute", "OrchestrationRouter", "RouteAction"]
