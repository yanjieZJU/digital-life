"""Planning task models facade."""

from __future__ import annotations

from ..types import OrchestrationPlan, TaskNode

TaskList = OrchestrationPlan
TaskDAG = OrchestrationPlan


__all__ = ["OrchestrationPlan", "TaskDAG", "TaskList", "TaskNode"]
