"""Recovery helpers for interrupted execution."""

from __future__ import annotations

from ..checklist import ExecutionStatus
from ..traces import ExecutionRepository, ExecutionTrace


class ExecutionRecoveryService:
    """Read open execution traces and render a compact recovery view."""

    def __init__(self, repository: ExecutionRepository) -> None:
        self._repository = repository

    def open_traces(self, agent_id: str | None = None) -> tuple[ExecutionTrace, ...]:
        return self._repository.list_open(agent_id=agent_id)

    def render_open_items(self, agent_id: str | None = None) -> str:
        traces = self.open_traces(agent_id)
        if not traces:
            return ""
        lines = ["## Open Execution Traces"]
        for trace in traces:
            lines.append(f"- trace={trace.id} event={trace.event_id} status={trace.status.value}")
            for item in trace.checklist:
                if item.status != ExecutionStatus.DONE:
                    lines.append(f"  - [{item.status.value}] {item.title}")
        return "\n".join(lines)


__all__ = ["ExecutionRecoveryService"]
