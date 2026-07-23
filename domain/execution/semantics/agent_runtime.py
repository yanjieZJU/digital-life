"""Generic agent runtime placeholder owned by Execution Semantics."""

from __future__ import annotations

from domain.core.models import AgentRun, AgentRunResult


class NoopAgentRuntime:
    """A deterministic placeholder for wiring tests."""

    def run(self, run: AgentRun) -> AgentRunResult:
        return AgentRunResult(
            run_id=run.id,
            status="noop",
            summary=f"noop runtime accepted event {run.event_id}",
        )


__all__ = ["NoopAgentRuntime"]

